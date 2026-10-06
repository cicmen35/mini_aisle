"""Hosted LLM via any OpenAI-compatible ``/chat/completions`` endpoint (OpenAI, Groq, OpenRouter...).

Used on the AWS demo env, where running Ollama would need a GPU instance.
"""

from __future__ import annotations

from typing import Any

import httpx

from patchloop_core.llm.base import CompletionRequest, CompletionResponse, LLMError


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        try:
            resp = self._client.post("/chat/completions", json=payload)
        except httpx.TransportError as exc:
            raise LLMError(f"llm endpoint unreachable: {exc}", retryable=True) from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise LLMError(f"llm {resp.status_code}: {resp.text[:200]}", retryable=True)
        if resp.status_code >= 400:
            raise LLMError(f"llm {resp.status_code}: {resp.text[:200]}", retryable=False)

        data = resp.json()
        usage = data.get("usage") or {}
        return CompletionResponse(
            text=data["choices"][0]["message"]["content"] or "",
            model=data.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    def close(self) -> None:
        self._client.close()
