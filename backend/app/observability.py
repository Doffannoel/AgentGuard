import json
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

from .config import settings

requests_total = Counter("requests_total", "Gateway requests")
requests_failed = Counter("requests_failed_total", "Failed gateway requests")
request_latency = Histogram("request_latency", "Gateway seconds")
provider_latency = Histogram("provider_latency", "Provider seconds")
tool_calls = Counter("tool_calls_total", "Proposed tool calls")
tool_denied = Counter("tool_denied_total", "Denied tool calls")
tool_approved = Counter("tool_approved_total", "Approved tool calls")
policy_latency = Histogram(
    "policy_latency", "Policy evaluation seconds", buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 1)
)
guard_findings = Counter("guard_findings_total", "Guard findings", ["type"])
replay_pass = Counter("replay_pass_total", "Replay passes")
replay_fail = Counter("replay_fail_total", "Replay failures")

provider = TracerProvider(resource=Resource.create({"service.name": "agentguard"}))
if settings.otlp_endpoint:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("agentguard")
logger = logging.getLogger("agentguard")


def log(event, **fields):
    logger.info(json.dumps({"level": "INFO", "event": event, **fields}))
