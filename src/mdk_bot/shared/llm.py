"""Stub for the Claude / Anthropic client used by future capabilities.

Phase 3+ will populate this with a real client. For now we expose the
interface so callers can be wired up against it without code change.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal LLM surface — every capability talks to this, not vendor SDKs."""

    async def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        """Return a model completion. Not implemented in Phase 0/1."""
        ...

    async def classify(self, text: str, labels: list[str]) -> str:
        """Pick the best label for ``text``. Not implemented in Phase 0/1."""
        ...


class NotConfiguredLLM:
    """Placeholder raised early so misuse is obvious in logs."""

    async def complete(self, prompt: str, *, max_tokens: int = 1024) -> str:
        raise NotImplementedError("LLM client not configured — wire up in Phase 3.")

    async def classify(self, text: str, labels: list[str]) -> str:
        raise NotImplementedError("LLM client not configured — wire up in Phase 3.")
