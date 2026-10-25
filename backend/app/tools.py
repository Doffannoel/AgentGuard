import json
from datetime import timedelta

from jsonschema import Draft202012Validator, SchemaError, ValidationError
from sqlalchemy import select

from .audit import append_event
from .config import settings
from .db import digest, now, project_lock, uid
from .errors import APIError
from .guards import inspect
from .models import Approval, GuardFinding, PolicyDecision, Tool, ToolCall, User
from .observability import guard_findings, tool_approved, tool_calls, tool_denied, tracer
from .policies import active_policy, evaluate


def registry_hash(tool):
    return digest(
        {
            "id": tool.id,
            "config": tool.config,
            "executor": tool.executor_type,
            "schema": tool.input_schema,
            "enabled": tool.enabled,
        }
    )


def register(db, project_id, name, data, user_id):
    project_lock(db, project_id)
    if name != data.name:
        raise APIError(422, "AG_INVALID_INPUT", "Tool names must match.")
    try:
        Draft202012Validator.check_schema(data.input_schema)
    except SchemaError as exc:
        raise APIError(422, "AG_INVALID_INPUT", "Invalid tool argument JSON Schema.") from exc
    schema = json.dumps(data.input_schema)
    if data.input_schema.get("type") != "object" or '"$ref"' in schema or '"$dynamicRef"' in schema:
        raise APIError(422, "AG_INVALID_INPUT", "Tool schemas must be objects without external references.")
    tool = db.scalar(select(Tool).where(Tool.project_id == project_id, Tool.name == name))
    if not tool:
        tool = Tool(project_id=project_id, name=name)
        db.add(tool)
    for field, value in data.model_dump().items():
        setattr(tool, field, value)
    db.flush()
    append_event(db, project_id, "TOOL_REGISTERED", {"tool": name, "user_id": user_id})
    db.commit()
    return {"id": tool.id, "name": tool.name, "enabled": tool.enabled}


def inspect_tool(db, project, request, actor="agent", version=None):
    redacted, findings = inspect(request.arguments)
    _, context_findings = inspect(request.context)
    findings += context_findings
    tool = db.scalar(
        select(Tool).where(Tool.project_id == project.id, Tool.name == request.tool, Tool.enabled.is_(True))
    )
    context = {
        "tenant": project.tenant_id,
        "project": project.id,
        "actor": {"id": actor},
        "tool": {"name": request.tool},
        "arguments": request.arguments,
        "environment": project.environment,
        "security": {"suspicious_input": any(f["type"] == "SUSPICIOUS_INSTRUCTION" for f in findings)},
    }
    result = evaluate(version.document if version else None, context)
    if not tool:
        result = {"decision": "DENY", "rule_id": None, "reason_code": "TOOL_NOT_REGISTERED"}
    else:
        try:
            Draft202012Validator(tool.input_schema).validate(request.arguments)
        except ValidationError:
            result = {"decision": "DENY", "rule_id": None, "reason_code": "INVALID_TOOL_ARGUMENTS"}
    return result, tool, redacted, findings


def authorize(db, key, request, request_id=None):
    with tracer.start_as_current_span("agentguard.tool"):
        project = project_lock(db, key.project_id)
        db.refresh(key)
        if not project.enabled or project.deleted_at or key.revoked_at:
            raise APIError(401, "AG_AUTH_401", "Project or API key is disabled.")
        version = active_policy(db, project.id)
        with tracer.start_as_current_span("policy"):
            result, tool, redacted, findings = inspect_tool(db, project, request, key.id, version)
        call = ToolCall(
            id=uid("call_"),
            project_id=project.id,
            request_id=request_id,
            api_key_id=key.id,
            tool_name=request.tool,
            arguments_redacted=redacted,
            arguments_hash=digest(request.arguments),
            context=inspect(request.context)[0],
            registry_hash=registry_hash(tool) if tool else "",
            status={"ALLOW": "AUTHORIZED", "DENY": "DENIED", "REQUIRE_APPROVAL": "APPROVAL_PENDING"}[
                result["decision"]
            ],
        )
        db.add(call)
        db.flush()
        decision = PolicyDecision(
            id=uid("dec_"),
            project_id=project.id,
            tool_call_id=call.id,
            policy_version_id=version.id if version else None,
            **result,
        )
        db.add(decision)
        payload = {
            **result,
            "tool": request.tool,
            "arguments": redacted,
            "request_id": request_id or call.id,
            "tool_call_id": call.id,
            "actor": key.id,
            "policy_version": version.id if version else "default",
            "findings": findings,
        }
        append_event(db, project.id, "TOOL_PROPOSED", payload)
        record_findings(db, project.id, call.id, findings)
        approval = None
        if result["decision"] == "REQUIRE_APPROVAL":
            approval = Approval(
                id=uid("apr_"),
                project_id=project.id,
                tool_call_id=call.id,
                policy_version_id=version.id if version else None,
                policy_rule_id=result["rule_id"],
                expires_at=now() + timedelta(seconds=settings.approval_seconds),
            )
            db.add(approval)
            append_event(db, project.id, "APPROVAL_REQUESTED", payload)
        else:
            append_event(
                db,
                project.id,
                "POLICY_ALLOWED" if result["decision"] == "ALLOW" else "POLICY_DENIED",
                payload,
            )
        tool_calls.inc()
        if result["decision"] == "DENY":
            tool_denied.inc()
        db.flush()
        return {
            **result,
            "decision_id": decision.id,
            "tool_call_id": call.id,
            "approval_id": approval.id if approval else None,
            "policy_version": version.id if version else None,
        }


def record_findings(db, project_id, request_id, findings):
    for finding in findings:
        db.add(GuardFinding(project_id=project_id, request_id=request_id, finding=finding))
        append_event(db, project_id, "GUARD_FINDING", {"request_id": request_id, "findings": [finding]})
        guard_findings.labels(finding["type"]).inc()


def resolve_approval(db, approval, user, action, comment):
    project_lock(db, approval.project_id)
    db.refresh(approval)
    if approval.status != "PENDING":
        raise APIError(409, "AG_APPROVAL_STATE", "Approval has already been resolved.")
    version = active_policy(db, approval.project_id)
    if approval.expires_at <= now() or approval.policy_version_id != (version.id if version else None):
        approval.status = "EXPIRED"
        append_event(db, approval.project_id, "APPROVAL_EXPIRED", {"approval_id": approval.id})
        db.commit()
        raise APIError(409, "AG_APPROVAL_EXPIRED", "Approval expired or policy changed; authorize again.")
    approval.status = "APPROVED" if action == "approve" else "REJECTED"
    approval.resolved_by, approval.resolved_at = user.id, now()
    approval.comment = inspect(comment)[0]
    call = db.get(ToolCall, approval.tool_call_id)
    call.status = "AUTHORIZED" if action == "approve" else "DENIED"
    append_event(
        db,
        approval.project_id,
        "APPROVAL_GRANTED" if action == "approve" else "APPROVAL_REJECTED",
        {
            "approval_id": approval.id,
            "tool": call.tool_name,
            "tool_call_id": call.id,
            "resolved_by": user.id,
            "policy_version": approval.policy_version_id,
            "comment": approval.comment,
        },
    )
    if action == "approve":
        tool_approved.inc()
    db.commit()
    return approval_view(db, approval)


def approval_view(db, approval):
    call = db.get(ToolCall, approval.tool_call_id)
    user = db.get(User, approval.resolved_by) if approval.resolved_by else None
    status = (
        "expired"
        if approval.status == "PENDING" and approval.expires_at <= now()
        else approval.status.lower()
    )
    args = call.arguments_redacted
    return {
        "id": approval.id,
        "title": call.tool_name,
        "agent": call.api_key_id,
        "customer": str(args.get("customer", "")),
        "amount": args.get("amount", 0) if isinstance(args.get("amount", 0), (int, float)) else 0,
        "reason": "Policy requires human approval.",
        "policy": approval.policy_rule_id or "default",
        "status": status,
        "resolvedBy": user.email if user else None,
        "resolvedAt": approval.resolved_at.isoformat() if approval.resolved_at else None,
        "comment": approval.comment,
        "expiresAt": approval.expires_at.isoformat() + "Z",
    }


def execute(db, key, request):
    project = project_lock(db, key.project_id)
    db.refresh(key)
    if not project.enabled or project.deleted_at or key.revoked_at:
        raise APIError(401, "AG_AUTH_401", "Project or API key is disabled.")
    if not request.tool_call_id:
        result = authorize(db, key, request)
        db.commit()
        if result["decision"] != "ALLOW":
            raise APIError(
                403,
                "AG_APPROVAL_REQUIRED" if result["decision"] == "REQUIRE_APPROVAL" else "AG_POLICY_403",
                "Tool execution is not authorized.",
                **result,
            )
        request.tool_call_id = result["tool_call_id"]
        project = project_lock(db, key.project_id)
    call = db.get(ToolCall, request.tool_call_id)
    if not call or call.project_id != key.project_id or call.api_key_id != key.id:
        raise APIError(404, "AG_NOT_FOUND", "Tool call not found.")
    if call.tool_name != request.tool or call.arguments_hash != digest(request.arguments):
        raise APIError(403, "AG_POLICY_403", "Tool name and arguments must match the authorized call.")
    if call.status != "AUTHORIZED" or call.created_at < now() - timedelta(seconds=settings.approval_seconds):
        raise APIError(409, "AG_APPROVAL_STATE", "Tool call is not executable or has expired.")
    version = active_policy(db, project.id)
    decision = db.scalar(select(PolicyDecision).where(PolicyDecision.tool_call_id == call.id))
    if decision.policy_version_id != (version.id if version else None):
        raise APIError(409, "AG_POLICY_CHANGED", "Policy changed; authorize again.")
    result, tool, _, _ = inspect_tool(db, project, request, key.id, version)
    if not tool or call.registry_hash != registry_hash(tool) or result["decision"] == "DENY":
        raise APIError(403, "AG_POLICY_403", "Tool disabled, changed, or denied.")
    if result["decision"] == "REQUIRE_APPROVAL":
        approval = db.scalar(select(Approval).where(Approval.tool_call_id == call.id))
        if not approval or approval.status != "APPROVED" or approval.expires_at <= now():
            raise APIError(403, "AG_APPROVAL_REQUIRED", "Valid human approval required.")
    with tracer.start_as_current_span("execution"):
        # Only a side-effect-free executor is installed. New executors must be server-owned allowlists.
        if tool.executor_type != "mock":
            raise APIError(422, "AG_EXECUTOR_UNAVAILABLE", "Executor is not installed.")
        output = {"mock": True, "tool": tool.name, "result": tool.config.get("result", {"ok": True})}
    call.status, call.completed_at = "EXECUTED", now()
    append_event(
        db,
        project.id,
        "TOOL_EXECUTED",
        {"tool": tool.name, "tool_call_id": call.id, "policy_version": decision.policy_version_id},
    )
    db.commit()
    return {"tool_call_id": call.id, "status": call.status, "output": output}
