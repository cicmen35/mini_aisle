"""Typed configuration, read from environment variables prefixed with ``PATCHLOOP_``.

Every service uses the same ``Settings`` object so that docker compose, kind and CI
configure the system the same way (12-factor style). See ``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PATCHLOOP_", extra="ignore")

    env: Literal["local", "test", "ci", "kind", "aws"] = "local"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://patchloop:patchloop@localhost:5432/patchloop"
    )
    db_pool_size: int = 5
    db_echo: bool = False

    aws_region: str = "eu-central-1"
    # None means "real AWS" (default endpoint resolution). LocalStack: http://localhost:4566
    aws_endpoint_url: str | None = None

    scan_queue_name: str = "patchloop-scan-requests"
    fix_queue_name: str = "patchloop-fix-requests"
    verify_queue_name: str = "patchloop-verify-requests"
    artifacts_bucket: str = "patchloop-artifacts"

    worker_wait_time_seconds: int = Field(default=20, ge=0, le=20)
    worker_max_messages: int = Field(default=5, ge=1, le=10)
    worker_visibility_timeout_seconds: int = Field(default=120, ge=0)
    worker_max_attempts: int = Field(default=5, ge=1)

    scanner_timeout_seconds: int = Field(default=300, ge=1)
    scanner_semgrep_config: str = "/opt/patchloop/rules/semgrep"

    llm_provider: Literal["mock", "ollama", "openai"] = "mock"
    llm_timeout_seconds: float = 120.0
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:1.5b"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: SecretStr | None = None

    api_max_upload_bytes: int = 20 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
