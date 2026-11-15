import pytest
from sylvie_runtime import ProviderRequestError, ProviderRouter

class FakeProvider:
    def __init__(self, name, answer=None, error=None):
        self.provider_name = name
        self.answer = answer
        self.error = error
        self.calls = 0
    def generate(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer

def test_router_uses_primary_first():
    primary = FakeProvider("openai", "primary answer")
    secondary = FakeProvider("anthropic", "secondary answer")
    router = ProviderRouter(primary, secondary)
    assert router.generate([{"role": "user", "content": "hello"}]) == "primary answer"
    assert primary.calls == 1
    assert secondary.calls == 0
    assert router.status()["last_used"] == "openai"

def test_router_falls_back_on_provider_request_error():
    primary = FakeProvider("openai", error=ProviderRequestError("offline"))
    secondary = FakeProvider("anthropic", "fallback answer")
    router = ProviderRouter(primary, secondary)
    assert router.generate([{"role": "user", "content": "hello"}]) == "fallback answer"
    assert router.status()["primary"] == "openai"
    assert router.status()["last_used"] == "anthropic"

def test_router_can_switch_primary():
    primary = FakeProvider("openai", "openai")
    secondary = FakeProvider("anthropic", "anthropic")
    router = ProviderRouter(primary, secondary)
    router.set_primary("anthropic")
    assert router.generate([{"role": "user", "content": "hello"}]) == "anthropic"
    assert router.status()["primary"] == "anthropic"

def test_router_does_not_fallback_on_programming_or_input_errors():
    primary = FakeProvider("openai", error=ValueError("invalid input"))
    secondary = FakeProvider("anthropic", "should not run")
    router = ProviderRouter(primary, secondary)
    with pytest.raises(ValueError):
        router.generate([{"role": "user", "content": "hello"}])
    assert secondary.calls == 0

def test_router_requires_unique_provider_names():
    with pytest.raises(ValueError):
        ProviderRouter(FakeProvider("same"), FakeProvider("same"))
