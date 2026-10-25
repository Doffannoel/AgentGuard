from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .db import canonical

Decision = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
Environment = Literal["production", "staging", "development"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def finite_json(self):
        canonical(self.model_dump())
        return self


class LoginInput(Input):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    environment: Environment = "development"
    provider: Literal["Mock", "OpenAI", "Ollama"] = "Mock"
    model: str = Field(default="mock-model", min_length=1, max_length=120)


class ProjectPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    environment: Environment | None = None
    provider: Literal["Mock", "OpenAI", "Ollama"] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None
    capture_mode: Literal["OFF", "REDACTED", "FULL"] | None = None
    requests_per_minute: int | None = Field(default=None, ge=1, le=100000)
    tokens_per_day: int | None = Field(default=None, ge=1)
    budget_per_day: float | None = Field(default=None, ge=0)


class KeyInput(Input):
    name: str = Field(min_length=1, max_length=120)
    environment: Literal["live", "test"] = "live"


class SimpleRule(Input):
    projectId: str
    description: str = Field(default="", max_length=4000)
    tool: str = Field(min_length=1, max_length=120)
    condition: str | None = Field(default=None, max_length=1000)
    effect: Decision
    enabled: bool = True


class PolicyInput(Input):
    projectId: str
    document: dict | list


class ToolInput(Input):
    name: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,120}$")
    description: str = Field(default="", max_length=4000)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    executor_type: Literal["mock"] = "mock"
    config: dict = Field(default_factory=dict)
    input_schema: dict = Field(default_factory=lambda: {"type": "object"})
    enabled: bool = True


class ToolRequest(Input):
    tool: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class SimulateInput(ToolRequest):
    projectId: str


class ExecuteInput(ToolRequest):
    tool_call_id: str | None = None


class ResolveInput(Input):
    comment: str | None = Field(default=None, max_length=4000)


class Message(Input):
    role: Literal["system", "developer", "user", "assistant", "tool"]
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


class CanonicalLLMRequest(Input):
    model: str = Field(min_length=1, max_length=120)
    messages: list[Message] = Field(min_length=1, max_length=1000)
    tools: list[dict] = Field(default_factory=list, max_length=100)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    stream: bool = False
    feature: str = Field(default="chat", max_length=120)

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, value):
        for tool in value:
            function = tool.get("function")
            if (
                tool.get("type") != "function"
                or not isinstance(function, dict)
                or not isinstance(function.get("name"), str)
            ):
                raise ValueError("Only named function tools are supported")
        return value


class CanonicalLLMResponse(Input):
    content: str | None = None
    tool_calls: list[dict] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    finish_reason: str = "stop"
    latency: int = 0
    provider_metadata: dict = Field(default_factory=dict)


class AttackInput(Input):
    projectId: str
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Tool Abuse", max_length=120)
    input: ToolRequest
    expected_tool: str = Field(min_length=1, max_length=120)
    expected_decision: Decision
    severity: Literal["low", "medium", "high", "critical"] = "high"
    source: str = Field(default="console", max_length=120)


class ReplayInput(Input):
    projectId: str
