from __future__ import annotations

from threading import RLock
from typing import Sequence
from .providers import ChatProvider, ProviderRequestError

class ProviderRouter:
    """Selects a preferred provider and optionally falls back on request failures.

    Failover is per request. It does not change the configured primary provider.
    """
    def __init__(self, primary: ChatProvider, secondary: ChatProvider | None = None,
                 *, automatic_fallback: bool = True) -> None:
        self._providers = {primary.provider_name: primary}
        if secondary is not None:
            if secondary.provider_name == primary.provider_name:
                raise ValueError("Primary and secondary providers must have different names.")
            self._providers[secondary.provider_name] = secondary
        self._primary_name = primary.provider_name
        self.automatic_fallback = automatic_fallback
        self._last_used: str | None = None
        self._last_fallback_error: str | None = None
        self._lock = RLock()

    def set_primary(self, provider_name: str) -> None:
        with self._lock:
            if provider_name not in self._providers:
                raise ValueError(f"Provider is not configured: {provider_name}")
            self._primary_name = provider_name

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        with self._lock:
            primary = self._providers[self._primary_name]
            secondary = next((p for name, p in self._providers.items()
                              if name != self._primary_name), None)
            try:
                answer = primary.generate(messages)
                self._last_used = primary.provider_name
                self._last_fallback_error = None
                return answer
            except ProviderRequestError as primary_error:
                self._last_fallback_error = str(primary_error)
                if not self.automatic_fallback or secondary is None:
                    raise
                try:
                    answer = secondary.generate(messages)
                except ProviderRequestError:
                    raise
                self._last_used = secondary.provider_name
                return answer

    @property
    def provider_name(self) -> str:
        return "router"

    def status(self) -> dict[str, str | bool | None]:
        with self._lock:
            secondary = next((name for name in self._providers if name != self._primary_name), None)
            return {
                "primary": self._primary_name,
                "secondary": secondary,
                "automatic_fallback": self.automatic_fallback,
                "last_used": self._last_used,
                "last_fallback_error": self._last_fallback_error,
            }
