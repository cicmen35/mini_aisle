from __future__ import annotations

import pytest

from patchloop_core.settings import Settings
from patchloop_core.storage import ArtifactNotFoundError, ArtifactStore, InMemoryArtifactStore


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATCHLOOP_AWS_ENDPOINT_URL", "http://localstack:4566")
    monkeypatch.setenv("PATCHLOOP_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("PATCHLOOP_DATABASE_URL", "postgresql+psycopg://u:secret@db/x")
    s = Settings()
    assert s.aws_endpoint_url == "http://localstack:4566"
    assert s.llm_provider == "ollama"
    assert "secret" not in repr(s)


def test_settings_reject_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATCHLOOP_WORKER_WAIT_TIME_SECONDS", "21")
    with pytest.raises(ValueError, match="worker_wait_time_seconds"):
        Settings()


def test_in_memory_store() -> None:
    store = InMemoryArtifactStore()
    assert isinstance(store, ArtifactStore)
    store.put_bytes("a/b", b"x")
    assert store.exists("a/b")
    assert store.get_bytes("a/b") == b"x"
    with pytest.raises(ArtifactNotFoundError):
        store.get_bytes("missing")
