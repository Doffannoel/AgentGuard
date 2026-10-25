import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import httpx

from .config import settings
from .errors import APIError
from .schemas import CanonicalLLMRequest, CanonicalLLMResponse


class ProviderAdapter(ABC):
    def supports_model(self, model: str) -> bool:
        return bool(model)

    @abstractmethod
    async def invoke(self, request: CanonicalLLMRequest) -> CanonicalLLMResponse: ...

    @abstractmethod
    def stream(self, request: CanonicalLLMRequest) -> AsyncIterator[dict]: ...


class MockProvider(ProviderAdapter):
    async def invoke(self, request):
        content = "Mock response: " + (request.messages[-1].content or "")
        return CanonicalLLMResponse(
            content=content,
            input_tokens=max(1, sum(len(m.content or "") for m in request.messages) // 4),
            output_tokens=min(request.max_tokens, max(1, len(content) // 4)),
        )

    async def stream(self, request):
        response = await self.invoke(request)
        yield {
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": response.content},
                    "finish_reason": None,
                }
            ]
        }
        yield {
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": response.input_tokens,
                "completion_tokens": response.output_tokens,
                "total_tokens": response.input_tokens + response.output_tokens,
            },
        }


class OpenAICompatibleProvider(ProviderAdapter):
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or settings.openai_base_url
        self.api_key = settings.openai_api_key if api_key is None else api_key

    def client(self):
        return httpx.AsyncClient(
            base_url=self.base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            timeout=httpx.Timeout(settings.provider_timeout, connect=5),
            follow_redirects=False,
            trust_env=False,
        )

    def payload(self, request):
        data = request.model_dump(exclude={"feature"}, exclude_none=True)
        if not data["tools"]:
            del data["tools"]
        if request.stream:
            data["stream_options"] = {"include_usage": True}
        return data

    async def invoke(self, request):
        try:
            async with asyncio.timeout(settings.provider_timeout), self.client() as client:
                response = await client.post("chat/completions", json=self.payload(request))
                response.raise_for_status()
                body = response.json()
                choice = body["choices"][0]
                usage = body.get("usage", {})
                return CanonicalLLMResponse(
                    content=choice["message"].get("content"),
                    tool_calls=choice["message"].get("tool_calls") or [],
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    finish_reason=choice.get("finish_reason") or "stop",
                    provider_metadata={"id": body.get("id")},
                )
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise APIError(504, "AG_PROVIDER_TIMEOUT", "Provider timed out.") from exc
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise APIError(502, "AG_PROVIDER_ERROR", "Provider returned an invalid response.") from exc

    async def stream(self, request):
        try:
            async with asyncio.timeout(settings.provider_timeout), self.client() as client:
                async with client.stream("POST", "chat/completions", json=self.payload(request)) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line[6:] != "[DONE]":
                            chunk = json.loads(line[6:])
                            if not isinstance(chunk, dict) or "error" in chunk:
                                raise ValueError("Invalid provider stream")
                            yield chunk
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise APIError(504, "AG_PROVIDER_TIMEOUT", "Provider stream timed out.") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise APIError(502, "AG_PROVIDER_ERROR", "Provider stream failed.") from exc


class OllamaProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(settings.ollama_base_url, "")


def resolve_provider(name):
    adapters = {"Mock": MockProvider, "OpenAI": OpenAICompatibleProvider, "Ollama": OllamaProvider}
    if name not in adapters:
        raise APIError(422, "AG_PROVIDER_ERROR", "Provider is not configured.")
    return adapters[name]()
