from __future__ import annotations
from typing import Protocol, Sequence

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
