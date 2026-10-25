import asyncio
import json

import httpx
import pytest

from app.providers import OllamaProvider, OpenAICompatibleProvider
from app.schemas import CanonicalLLMRequest


@pytest.mark.parametrize("adapter_type", [OpenAICompatibleProvider, OllamaProvider])
def test_provider_http_protocol(adapter_type, monkeypatch):
    adapter = adapter_type()

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model" and "feature" not in payload
        if payload["stream"]:
            assert payload["stream_options"]["include_usage"]
            chunk = {
                "choices": [{"delta": {"content": "Hello"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }
            return httpx.Response(
                200,
                text="data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n",
                headers={"Content-Type": "text/event-stream"},
            )
        return httpx.Response(
            200,
            json={
                "id": "provider-id",
                "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    monkeypatch.setattr(
        adapter,
        "client",
        lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://provider.example/v1/"
        ),
    )
    request = CanonicalLLMRequest(model="test-model", messages=[{"role": "user", "content": "Hi"}])
    response = asyncio.run(adapter.invoke(request))
    assert response.content == "Hello" and response.input_tokens == 3 and response.output_tokens == 2

    async def chunks():
        return [chunk async for chunk in adapter.stream(request.model_copy(update={"stream": True}))]

    assert asyncio.run(chunks())[0]["choices"][0]["delta"]["content"] == "Hello"
