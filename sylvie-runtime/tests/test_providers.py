import json
import pytest
from sylvie_runtime import (
    AnthropicChatProvider, OpenAIChatProvider, ProviderRequestError,
)

class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.request = None
    def __call__(self, request, timeout):
        self.request = request
        return json.dumps(self.response).encode("utf-8")

def test_openai_adapter_formats_request_and_reads_text():
    transport = FakeTransport({"choices": [{"message": {"content": "Hello from OpenAI"}}]})
    provider = OpenAIChatProvider("test-model", api_key="test-secret", transport=transport)
    result = provider.generate([{"role": "system", "content": "Be helpful"},
                                {"role": "user", "content": "Hello"}])
    assert result == "Hello from OpenAI"
    assert transport.request.full_url.endswith("/v1/chat/completions")
    assert transport.request.get_header("Authorization") == "Bearer test-secret"
    payload = json.loads(transport.request.data)
    assert payload["messages"][0]["role"] == "system"
    assert "tools" not in payload

def test_anthropic_adapter_moves_system_prompt_to_top_level():
    transport = FakeTransport({"content": [{"type": "text", "text": "Hello from Anthropic"}]})
    provider = AnthropicChatProvider("test-model", api_key="test-secret", transport=transport)
    result = provider.generate([{"role": "system", "content": "Be helpful"},
                                {"role": "user", "content": "Hello"}])
    assert result == "Hello from Anthropic"
    assert transport.request.full_url.endswith("/v1/messages")
    assert transport.request.get_header("X-api-key") == "test-secret"
    payload = json.loads(transport.request.data)
    assert payload["system"] == "Be helpful"
    assert payload["messages"] == [{"role": "user", "content": "Hello"}]
    assert "tools" not in payload

def test_provider_requires_key_and_model():
    with pytest.raises(ValueError):
        OpenAIChatProvider("model", api_key="")
    with pytest.raises(ValueError):
        AnthropicChatProvider("", api_key="secret")

def test_provider_rejects_malformed_response():
    transport = FakeTransport({"unexpected": True})
    provider = OpenAIChatProvider("test-model", api_key="test-secret", transport=transport)
    with pytest.raises(ProviderRequestError):
        provider.generate([{"role": "user", "content": "Hello"}])
