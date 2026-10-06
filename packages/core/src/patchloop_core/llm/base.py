"""LLM provider contract. The fixer depends on this, so Ollama / mock / a hosted API are swappable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.0
    max_tokens: int = 2048
    # Free-form tags (e.g. rule_id, finding_id). Providers may log them; the mock can key on them.
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompletionResponse:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMError(RuntimeError):
    """Provider failed. ``retryable`` tells the worker whether to retry or give up."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, request: CompletionRequest) -> CompletionResponse: ...
