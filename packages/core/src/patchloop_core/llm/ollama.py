"""Ollama provider (local models, zero cost). API: https://github.com/ollama/ollama/blob/main/docs/api.md"""

from __future__ import annotations

from typing import Any

import httpx

from patchloop_core.llm.base import CompletionRequest, CompletionResponse, LLMError


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds, transport=transport
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        try:
            resp = self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(f"ollama timed out: {exc}", retryable=True) from exc
        except httpx.TransportError as exc:
            raise LLMError(f"ollama unreachable: {exc}", retryable=True) from exc

        if resp.status_code >= 500:
            raise LLMError(f"ollama {resp.status_code}: {resp.text[:200]}", retryable=True)
        if resp.status_code >= 400:
            raise LLMError(f"ollama {resp.status_code}: {resp.text[:200]}", retryable=False)

        data = resp.json()
        return CompletionResponse(
            text=data.get("message", {}).get("content", ""),
            model=data.get("model", self.model),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )

    def close(self) -> None:
        self._client.close()
