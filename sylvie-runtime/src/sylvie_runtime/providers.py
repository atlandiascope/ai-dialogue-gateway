from __future__ import annotations

import json
import os
from typing import Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ChatProvider(Protocol):
    """Adapter contract. Implementations must not execute tools implicitly."""
    provider_name: str

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        """Return assistant text for the supplied role/content messages."""
        ...

class LocalTestProvider:
    """Deterministic offline provider for development and automated tests."""
    provider_name = "local-test"

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if not last_user.strip():
            return "I'm Sylvie's local test provider. Send a message to begin."
        return f"Local test response: {last_user.strip()}"


class ProviderRequestError(RuntimeError):
    """A provider request failed or returned an unsupported response."""


Transport = Callable[[Request, float], bytes]

def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read(2_000_001)

def _post_json(url: str, headers: dict[str, str], payload: dict, *, timeout: float, transport: Transport) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
    try:
        raw = transport(request, timeout)
    except HTTPError as exc:
        # Do not echo response bodies: providers may include sensitive request context.
        raise ProviderRequestError(f"Provider returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise ProviderRequestError(f"Provider connection failed: {type(exc).__name__}.") from None
    if len(raw) > 2_000_000:
        raise ProviderRequestError("Provider response exceeded the 2 MB limit.")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderRequestError("Provider returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise ProviderRequestError("Provider returned an unexpected response format.")
    return data

def _validate_messages(messages: Sequence[dict[str, str]]) -> None:
    for message in messages:
        if message.get("role") not in {"system", "user", "assistant"}:
            raise ValueError("Only system, user, and assistant messages are supported.")
        if not isinstance(message.get("content"), str):
            raise ValueError("Every message must have string content.")

class OpenAIChatProvider:
    """OpenAI Chat Completions adapter. No tools or function calls are enabled."""
    provider_name = "openai"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model: str, *, api_key: str | None = None, timeout: float = 45.0,
                 max_completion_tokens: int = 1024, transport: Transport = _default_transport) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY or pass api_key securely at runtime.")
        if not model.strip():
            raise ValueError("An OpenAI model name is required.")
        self.model, self.timeout = model, timeout
        self.max_completion_tokens, self.transport = max_completion_tokens, transport

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        _validate_messages(messages)
        payload = {"model": self.model, "messages": list(messages),
                   "max_completion_tokens": self.max_completion_tokens, "stream": False}
        data = _post_json(self.endpoint, {"Authorization": f"Bearer {self.api_key}"}, payload,
                          timeout=self.timeout, transport=self.transport)
        try:
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderRequestError("OpenAI response did not contain assistant text.") from None
        if not isinstance(answer, str) or not answer.strip():
            raise ProviderRequestError("OpenAI returned an empty or non-text response.")
        return answer

class AnthropicChatProvider:
    """Anthropic Messages API adapter. No tools are enabled."""
    provider_name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str, *, api_key: str | None = None, timeout: float = 45.0,
                 max_tokens: int = 1024, transport: Transport = _default_transport) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set ANTHROPIC_API_KEY or pass api_key securely at runtime.")
        if not model.strip():
            raise ValueError("An Anthropic model name is required.")
        self.model, self.timeout = model, timeout
        self.max_tokens, self.transport = max_tokens, transport

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        _validate_messages(messages)
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        conversation = [{"role": m["role"], "content": m["content"]}
                        for m in messages if m["role"] != "system"]
        if not conversation:
            raise ValueError("At least one user or assistant message is required.")
        payload = {"model": self.model, "max_tokens": self.max_tokens, "messages": conversation}
        if system:
            payload["system"] = system
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        data = _post_json(self.endpoint, headers, payload, timeout=self.timeout, transport=self.transport)
        try:
            blocks = data["content"]
            answer = "".join(block["text"] for block in blocks if block.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderRequestError("Anthropic response did not contain text content.") from None
        if not answer.strip():
            raise ProviderRequestError("Anthropic returned an empty response.")
        return answer