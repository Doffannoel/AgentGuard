from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, uid


class Identity:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)


class Tenant(Identity, Base):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(120))


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class TenantMember(Base):
    __tablename__ = "tenant_members"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="admin")


class ConsoleSession(Identity, Base):
    __tablename__ = "console_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    window: Mapped[datetime] = mapped_column(default=now)


class Project(Identity, Base):
    __tablename__ = "projects"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(String(20), default="development")
    provider: Mapped[str] = mapped_column(String(40), default="Mock")
    model: Mapped[str] = mapped_column(String(120), default="mock-model")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    capture_mode: Mapped[str] = mapped_column(String(10), default="REDACTED")
    requests_per_minute: Mapped[int] = mapped_column(default=60)
    tokens_per_day: Mapped[int] = mapped_column(default=1_000_000)
    budget_per_day: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    audit_head: Mapped[str] = mapped_column(String(64), default="")
    audit_count: Mapped[int] = mapped_column(default=0)


class ApiKey(Identity, Base):
    __tablename__ = "api_keys"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(64), unique=True)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    environment: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(default=now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)


class Policy(Identity, Base):
    __tablename__ = "policies"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), unique=True)
    active_version: Mapped[int] = mapped_column(default=0)


class PolicyVersion(Identity, Base):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "version"),)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"))
    version: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Tool(Identity, Base):
    __tablename__ = "tools"
    __table_args__ = (UniqueConstraint("project_id", "name"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    executor_type: Mapped[str] = mapped_column(String(20), default="mock")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    input_schema: Mapped[dict] = mapped_column(JSON, default=lambda: {"type": "object"})
    enabled: Mapped[bool] = mapped_column(default=True)


class LLMRequest(Identity, Base):
    __tablename__ = "llm_requests"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    api_key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    environment: Mapped[str] = mapped_column(String(20))
    feature: Mapped[str] = mapped_column(String(120), default="chat")
    request_hash: Mapped[str] = mapped_column(String(64))
    capture: Mapped[dict | None] = mapped_column(JSON)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    reserved_tokens: Mapped[int] = mapped_column(default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    pricing_configured: Mapped[bool] = mapped_column(default=False)
    reserved_cost: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    trace_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=now, index=True)


class ToolCall(Identity, Base):
    __tablename__ = "tool_calls"
    request_id: Mapped[str | None] = mapped_column(ForeignKey("llm_requests.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    api_key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"))
    tool_name: Mapped[str] = mapped_column(String(120))
    arguments_redacted: Mapped[dict] = mapped_column(JSON)
    arguments_hash: Mapped[str] = mapped_column(String(64))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    registry_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class PolicyDecision(Identity, Base):
    __tablename__ = "policy_decisions"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    tool_call_id: Mapped[str | None] = mapped_column(ForeignKey("tool_calls.id"))
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"))
    decision: Mapped[str] = mapped_column(String(30))
    rule_id: Mapped[str | None] = mapped_column(String(120))
    reason_code: Mapped[str] = mapped_column(String(120))


class Approval(Identity, Base):
    __tablename__ = "approval_requests"
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"))
    policy_rule_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    requested_at: Mapped[datetime] = mapped_column(default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)


class GuardFinding(Identity, Base):
    __tablename__ = "guard_findings"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    finding: Mapped[dict] = mapped_column(JSON)


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("project_id", "sequence"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(default=now)
    payload: Mapped[dict] = mapped_column(JSON)
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))


class AttackCase(Identity, Base):
    __tablename__ = "attack_cases"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(120))
    input: Mapped[dict] = mapped_column(JSON)
    expected_tool: Mapped[str] = mapped_column(String(120))
    expected_decision: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(20), default="high")
    source: Mapped[str] = mapped_column(String(120), default="console")


class ReplayRun(Identity, Base):
    __tablename__ = "replay_runs"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("policy_versions.id"))
    case_snapshot: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)


class ReplayResult(Identity, Base):
    __tablename__ = "replay_results"
    run_id: Mapped[str] = mapped_column(ForeignKey("replay_runs.id"), index=True)
    attack_case_id: Mapped[str] = mapped_column(ForeignKey("attack_cases.id"))
    expected: Mapped[str] = mapped_column(String(30))
    actual: Mapped[str] = mapped_column(String(30))
    passed: Mapped[bool] = mapped_column(Boolean)
    latency: Mapped[int] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)


class ModelPricing(Identity, Base):
    __tablename__ = "model_pricing"
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    input_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    output_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    effective_from: Mapped[datetime] = mapped_column(default=now)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    minute: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
