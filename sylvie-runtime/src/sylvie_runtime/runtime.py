from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
from .providers import ChatProvider

@dataclass(frozen=True)
class Message:
    role: str
    content: str
    created_at: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

@dataclass
class Conversation:
    conversation_id: str
    messages: list[Message] = field(default_factory=list)

class SylvieRuntime:
    """Small conversation coordinator; sessions are in-memory and process-local."""
    def __init__(self, provider: ChatProvider, *, persona: str = "You are Sylvie, a helpful, honest assistant.",
                 max_history_messages: int = 20, max_message_chars: int = 8000) -> None:
        if max_history_messages < 2 or max_message_chars < 1:
            raise ValueError("History and message limits must be positive.")
        self.provider = provider
        self.persona = persona.strip()
        self.max_history_messages = max_history_messages
        self.max_message_chars = max_message_chars
        self._sessions: dict[str, Conversation] = {}
        self._lock = RLock()

    def create_conversation(self) -> str:
        conversation_id = uuid4().hex
        with self._lock:
            self._sessions[conversation_id] = Conversation(conversation_id)
        return conversation_id

    def get_history(self, conversation_id: str) -> list[Message]:
        with self._lock:
            conversation = self._get(conversation_id)
            return list(conversation.messages)

    def _get(self, conversation_id: str) -> Conversation:
        conversation = self._sessions.get(conversation_id)
        if conversation is None:
            raise KeyError("Conversation not found in this runtime process.")
        return conversation

    def send(self, conversation_id: str, content: str) -> Message:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Message cannot be empty.")
        if len(content) > self.max_message_chars:
            raise ValueError("Message exceeds the configured character limit.")
        with self._lock:
            conversation = self._get(conversation_id)
            prior = conversation.messages[-self.max_history_messages:]
            request = [{"role": "system", "content": self.persona}]
            request.extend(message.as_dict() for message in prior)
            request.append({"role": "user", "content": content.strip()})
            # Keep the lock while generating to preserve message ordering per session.
            response_text = self.provider.generate(request)
            if not isinstance(response_text, str) or not response_text.strip():
                raise RuntimeError("Provider returned an empty or invalid response.")
            now = datetime.now(timezone.utc).isoformat()
            user_message = Message("user", content.strip(), now)
            assistant_message = Message("assistant", response_text.strip(), datetime.now(timezone.utc).isoformat())
            conversation.messages.extend((user_message, assistant_message))
            # Retain a bounded transcript; the next request includes at most this many.
            conversation.messages = conversation.messages[-self.max_history_messages:]
            return assistant_message

    def provider_status(self) -> dict[str, str]:
        return {"provider": str(getattr(self.provider, "provider_name", "custom")), "mode": "configured"}
