"""Deterministic provider for tests and CI: no network, no model download."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from patchloop_core.llm.base import CompletionRequest, CompletionResponse

DEFAULT_MOCK_RESPONSE = "I could not produce a patch for this finding."


class MockLLMProvider:
    """Returns canned text.

    Resolution order: ``responder(request)`` if given, else ``responses[metadata["rule_id"]]``,
    else ``default``. Every request is recorded in ``calls`` for assertions.
    """

    name = "mock"

    def __init__(
        self,
        *,
        responses: Mapping[str, str] | None = None,
        default: str = DEFAULT_MOCK_RESPONSE,
        responder: Callable[[CompletionRequest], str] | None = None,
    ) -> None:
        self._responses = dict(responses or {})
        self._default = default
        self._responder = responder
        self.calls: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls.append(request)
        if self._responder is not None:
            text = self._responder(request)
        else:
            text = self._responses.get(request.metadata.get("rule_id", ""), self._default)
        return CompletionResponse(text=text, model="mock-1")
