from patchloop_core.llm.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    LLMError,
    LLMProvider,
)
from patchloop_core.llm.mock import MockLLMProvider
from patchloop_core.llm.ollama import OllamaProvider
from patchloop_core.llm.openai_compat import OpenAICompatibleProvider
from patchloop_core.settings import Settings


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if settings.llm_provider == "openai":
        if settings.openai_api_key is None:
            raise ValueError(
                "PATCHLOOP_OPENAI_API_KEY is required when PATCHLOOP_LLM_PROVIDER=openai"
            )
        return OpenAICompatibleProvider(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return MockLLMProvider()


__all__ = [
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "LLMError",
    "LLMProvider",
    "MockLLMProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "build_llm_provider",
]
