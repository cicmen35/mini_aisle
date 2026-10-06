from __future__ import annotations

import json

import httpx
import pytest

from patchloop_core.llm import (
    ChatMessage,
    CompletionRequest,
    LLMError,
    LLMProvider,
    MockLLMProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    build_llm_provider,
)
from patchloop_core.settings import Settings

REQ = CompletionRequest(
    messages=(ChatMessage("system", "only diffs"), ChatMessage("user", "fix it")),
    metadata={"rule_id": "B602"},
)


def test_mock_is_deterministic_and_records_calls() -> None:
    llm = MockLLMProvider(responses={"B602": "```diff\n...\n```"})
    assert isinstance(llm, LLMProvider)
    assert llm.complete(REQ).text.startswith("```diff")
    assert (
        llm.complete(CompletionRequest(messages=())).text
        == llm.complete(CompletionRequest(messages=())).text
    )
    assert len(llm.calls) == 3


def test_ollama_request_shape_and_response_parsing() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"model": "m", "message": {"content": "hi"}, "eval_count": 3}
        )

    llm = OllamaProvider(
        base_url="http://ollama:11434/", model="m", transport=httpx.MockTransport(handler)
    )
    resp = llm.complete(REQ)
    assert resp.text == "hi"
    assert resp.completion_tokens == 3
    assert seen["path"] == "/api/chat"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["stream"] is False
    assert body["messages"][0] == {"role": "system", "content": "only diffs"}


@pytest.mark.parametrize(
    ("status", "retryable"), [(500, True), (503, True), (400, False), (404, False)]
)
def test_ollama_error_classification(status: int, retryable: bool) -> None:
    llm = OllamaProvider(
        base_url="http://x",
        model="m",
        transport=httpx.MockTransport(lambda _r: httpx.Response(status, text="boom")),
    )
    with pytest.raises(LLMError) as exc:
        llm.complete(REQ)
    assert exc.value.retryable is retryable


def test_ollama_connection_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    llm = OllamaProvider(base_url="http://x", model="m", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError) as exc:
        llm.complete(REQ)
    assert exc.value.retryable


def test_openai_compatible_provider() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-test"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200, json={"model": "gpt", "choices": [{"message": {"content": "ok"}}]}
        )

    llm = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="gpt",
        transport=httpx.MockTransport(handler),
    )
    assert llm.complete(REQ).text == "ok"


def test_openai_rate_limit_is_retryable() -> None:
    llm = OpenAICompatibleProvider(
        base_url="https://x/v1",
        api_key="k",
        model="m",
        transport=httpx.MockTransport(lambda _r: httpx.Response(429)),
    )
    with pytest.raises(LLMError) as exc:
        llm.complete(REQ)
    assert exc.value.retryable


def test_factory_selects_provider() -> None:
    assert build_llm_provider(Settings(llm_provider="mock")).name == "mock"
    assert build_llm_provider(Settings(llm_provider="ollama")).name == "ollama"
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_llm_provider(Settings(llm_provider="openai"))
