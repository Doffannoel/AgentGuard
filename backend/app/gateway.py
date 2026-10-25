import asyncio
import json
import time

from fastapi.responses import StreamingResponse
from sqlalchemy import select

from . import observability as obs
from .audit import append_event
from .db import digest, project_lock, uid
from .errors import APIError
from .guards import inspect, token_ceiling
from .models import LLMRequest, Tool
from .policies import active_policy, evaluate
from .providers import resolve_provider
from .schemas import CanonicalLLMRequest, CanonicalLLMResponse, ToolRequest
from .tools import authorize, record_findings
from .usage import cost, rate_limit, reserve


def prepare(db, key, request, trace_id, request_id):
    project = project_lock(db, key.project_id)
    if request.model != project.model:
        raise APIError(403, "AG_MODEL_DENIED", "Model is not enabled for this project.")
    raw = request.model_dump()
    messages, findings = inspect(raw["messages"])
    redacted = {**raw, "messages": messages}
    redacted["feature"] = inspect(raw["feature"])[0]
    # Tool definitions come from the registry, never from agent-provided URLs or schemas.
    registered = []
    for definition in request.tools:
        name = definition["function"]["name"]
        tool = db.scalar(
            select(Tool).where(Tool.project_id == project.id, Tool.name == name, Tool.enabled.is_(True))
        )
        if not tool:
            raise APIError(403, "AG_POLICY_403", "Only registered tools may be proposed.")
        registered.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": inspect(tool.description)[0],
                    "parameters": tool.input_schema,
                },
            }
        )
    redacted["tools"] = registered
    clean = CanonicalLLMRequest.model_validate(redacted)
    version = active_policy(db, project.id)
    decision = evaluate(
        version.document if version else None,
        {
            "tenant": project.tenant_id,
            "project": project.id,
            "actor": {"id": key.id},
            "environment": project.environment,
            "security": {"suspicious_input": any(f["type"] == "SUSPICIOUS_INSTRUCTION" for f in findings)},
            "arguments": {},
        },
        "llm",
    )
    record = LLMRequest(
        id=request_id,
        tenant_id=project.tenant_id,
        project_id=project.id,
        api_key_id=key.id,
        provider=project.provider,
        model=request.model,
        environment=project.environment,
        feature=clean.feature,
        request_hash=digest(raw),
        trace_id=trace_id,
        capture=None
        if project.capture_mode == "OFF"
        else raw
        if project.capture_mode == "FULL"
        else redacted,
    )
    if decision["decision"] != "ALLOW":
        append_event(
            db,
            project.id,
            "POLICY_DENIED",
            {**decision, "request_id": record.id, "policy_version": version.id if version else "default"},
        )
        db.commit()
        raise APIError(403, "AG_POLICY_403", "LLM request denied by policy.")
    try:
        price = reserve(db, project, record, token_ceiling(redacted), request.max_tokens)
    except APIError as exc:
        record_findings(
            db,
            project.id,
            record.id,
            [{"type": "BUDGET_VIOLATION", "detected": exc.code, "action": "BLOCKED", "severity": "high"}],
        )
        append_event(db, project.id, "POLICY_DENIED", {"request_id": record.id, "reason_code": exc.code})
        db.commit()
        raise
    append_event(
        db,
        project.id,
        "REQUEST_ACCEPTED",
        {
            "request_id": record.id,
            "trace_id": trace_id,
            "model": request.model,
            "policy_version": version.id if version else "default",
        },
    )
    record_findings(db, project.id, record.id, findings)
    db.commit()
    return record, clean, price


def finish(db, record, response, price, started, success):
    project_lock(db, record.project_id)
    record.status = "COMPLETED" if success else "FAILED"
    record.latency_ms = round((time.perf_counter() - started) * 1000)
    record.input_tokens, record.output_tokens = response.input_tokens, response.output_tokens
    record.estimated_cost = cost(price, response.input_tokens, response.output_tokens)
    # Missing usage (including disconnects) keeps a conservative reservation for the day.
    if response.input_tokens + response.output_tokens > 0:
        record.reserved_tokens = response.input_tokens + response.output_tokens
        record.reserved_cost = record.estimated_cost
    append_event(
        db,
        record.project_id,
        "REQUEST_COMPLETED" if success else "REQUEST_FAILED",
        {
            "request_id": record.id,
            "trace_id": record.trace_id,
            "latency_ms": record.latency_ms,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "estimated_cost": str(record.estimated_cost),
        },
    )
    db.commit()
    obs.request_latency.observe(record.latency_ms / 1000)
    if not success:
        obs.requests_failed.inc()
    obs.log(
        "request_completed",
        request_id=record.id,
        trace_id=record.trace_id,
        project_id=record.project_id,
        status=record.status,
    )


def authorize_output(db, key, record, calls):
    results = []
    for call in calls:
        try:
            function = call["function"]
            arguments = json.loads(function["arguments"])
            request = ToolRequest(tool=function["name"], arguments=arguments)
        except (KeyError, ValueError, TypeError) as exc:
            raise APIError(502, "AG_PROVIDER_ERROR", "Provider returned invalid tool arguments.") from exc
        results.append({"provider_tool_call_id": call.get("id"), **authorize(db, key, request, record.id)})
    db.commit()
    return results


async def chat(db, key, request, request_id=None):
    rate_limit(db, key)
    started = time.perf_counter()
    obs.requests_total.inc()
    with obs.tracer.start_as_current_span("agentguard.request") as span:
        trace_id = f"{span.get_span_context().trace_id:032x}"
        with obs.tracer.start_as_current_span("guard"):
            record, clean, price = prepare(db, key, request, trace_id, request_id or uid("req_"))
        adapter = resolve_provider(record.provider)
        if request.stream:
            return StreamingResponse(
                stream_response(db, key, record, clean, price, adapter, started),
                media_type="text/event-stream",
                headers={"X-Request-ID": record.id, "Cache-Control": "no-store"},
            )
        response = CanonicalLLMResponse()
        try:
            with obs.tracer.start_as_current_span("provider"):
                response = await adapter.invoke(clean)
            obs.provider_latency.observe(time.perf_counter() - started)
            decisions = authorize_output(db, key, record, response.tool_calls)
            message = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                message["tool_calls"] = response.tool_calls
            finish(db, record, response, price, started, True)
            return {
                "id": record.id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": clean.model,
                "choices": [{"index": 0, "message": message, "finish_reason": response.finish_reason}],
                "usage": {
                    "prompt_tokens": response.input_tokens,
                    "completion_tokens": response.output_tokens,
                    "total_tokens": response.input_tokens + response.output_tokens,
                },
                "agentguard": {
                    "request_id": record.id,
                    "trace_id": trace_id,
                    "tool_decisions": decisions,
                    "pricing_configured": price is not None,
                },
            }
        except (APIError, asyncio.CancelledError):
            finish(db, record, response, price, started, False)
            raise


async def stream_response(db, key, record, request, price, adapter, started):
    response = CanonicalLLMResponse()
    calls = {}
    success = False
    stream_bytes = 0
    try:
        with obs.tracer.start_as_current_span("provider.stream"):
            async for chunk in adapter.stream(request):
                stream_bytes += len(json.dumps(chunk))
                if stream_bytes > 8_388_608:
                    raise APIError(502, "AG_PROVIDER_ERROR", "Provider stream exceeded the response limit.")
                if chunk.get("usage"):
                    usage = chunk["usage"]
                    response.input_tokens = max(0, int(usage.get("prompt_tokens", 0)))
                    response.output_tokens = max(0, int(usage.get("completion_tokens", 0)))
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta", {})
                    for fragment in delta.get("tool_calls", []):
                        index = fragment["index"]
                        call = calls.setdefault(
                            index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                        )
                        call["id"] += fragment.get("id", "")
                        for field in ("name", "arguments"):
                            call["function"][field] += fragment.get("function", {}).get(field, "")
                # Streamed proposals never grant execution permission; use /tools/execute.
                yield (
                    "data: "
                    + json.dumps(
                        {**chunk, "id": record.id, "model": request.model, "object": "chat.completion.chunk"}
                    )
                    + "\n\n"
                )
        decisions = authorize_output(db, key, record, list(calls.values()))
        success = True
        yield (
            "data: "
            + json.dumps({"id": record.id, "choices": [], "agentguard": {"tool_decisions": decisions}})
            + "\n\n"
        )
        yield "data: [DONE]\n\n"
    except APIError as exc:
        yield (
            "data: "
            + json.dumps({"error": {"code": exc.code, "message": exc.message, "request_id": record.id}})
            + "\n\n"
        )
    except (KeyError, TypeError, ValueError):
        yield (
            "data: "
            + json.dumps(
                {
                    "error": {
                        "code": "AG_PROVIDER_ERROR",
                        "message": "Invalid provider stream.",
                        "request_id": record.id,
                    }
                }
            )
            + "\n\n"
        )
    finally:
        obs.provider_latency.observe(time.perf_counter() - started)
        finish(db, record, response, price, started, success)
