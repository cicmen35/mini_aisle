"""The real adapters (SQS, S3, Postgres, Alembic) against compose services."""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect

from patchloop_core.db.migrate import main as migrate
from patchloop_core.db.session import create_db_engine, create_session_factory, ping
from patchloop_core.queue import QueueClient, ReceivedMessage, SqsQueue
from patchloop_core.settings import Settings
from patchloop_core.storage import ArtifactNotFoundError, ArtifactStore, S3ArtifactStore
from patchloop_core.worker import PostgresIdempotencyStore

pytestmark = pytest.mark.integration


def test_sqs_round_trip(temp_queue_with_dlq: tuple[SqsQueue, SqsQueue]) -> None:
    queue, _ = temp_queue_with_dlq
    assert isinstance(queue, QueueClient)
    queue.send('{"hello": "world"}')
    [msg] = queue.receive(wait_time_seconds=2, visibility_timeout=30)
    assert msg.body == '{"hello": "world"}'
    assert msg.receive_count == 1
    queue.ack(msg)
    assert queue.receive(wait_time_seconds=1) == []


def test_visibility_timeout_and_redrive_to_dlq(
    temp_queue_with_dlq: tuple[SqsQueue, SqsQueue],
) -> None:
    """At-least-once delivery: un-acked messages come back, and after maxReceiveCount go to the DLQ."""
    queue, dlq = temp_queue_with_dlq
    queue.send("poison")
    for attempt in (1, 2):
        [msg] = queue.receive(wait_time_seconds=2, visibility_timeout=1)
        assert msg.receive_count == attempt
        time.sleep(1.5)  # don't ack: simulate a crashing consumer
    assert queue.receive(wait_time_seconds=1, visibility_timeout=1) == []
    deadline = time.monotonic() + 10
    moved: list[ReceivedMessage] = []
    while not moved and time.monotonic() < deadline:
        moved = dlq.receive(wait_time_seconds=1)
    assert [m.body for m in moved] == ["poison"]


def test_s3_round_trip(settings: Settings) -> None:
    store = S3ArtifactStore.from_settings(settings)
    assert isinstance(store, ArtifactStore)
    key = f"test/{uuid4()}.txt"
    assert not store.exists(key)
    store.put_bytes(key, b"patch", content_type="text/x-diff")
    assert store.exists(key)
    assert store.get_bytes(key) == b"patch"
    with pytest.raises(ArtifactNotFoundError):
        store.get_bytes(f"test/{uuid4()}")


def test_database_reachable_and_migrations_apply(
    engine: Engine, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    ping(engine)
    monkeypatch.setenv("PATCHLOOP_DATABASE_URL", settings.database_url.get_secret_value())
    migrate(["head"])
    assert "alembic_version" in inspect(engine).get_table_names()


@pytest.mark.todo
def test_core_tables_exist_after_migration(engine: Engine) -> None:
    """Done when Šimon's first migration creates the schema from models.py."""
    tables = set(inspect(engine).get_table_names())
    missing = {"jobs", "findings", "patches", "processed_messages"} - tables
    if missing:
        raise NotImplementedError(f"TODO(simon): models + migration for {sorted(missing)}")


@pytest.mark.todo
def test_postgres_idempotency_store_survives_new_instances(settings: Settings) -> None:
    factory = create_session_factory(create_db_engine(settings))
    key = f"test:{uuid4()}"
    assert not PostgresIdempotencyStore(factory).is_processed(key)
    PostgresIdempotencyStore(factory).mark_processed(key)
    PostgresIdempotencyStore(factory).mark_processed(key)  # idempotent itself
    assert PostgresIdempotencyStore(factory).is_processed(key)
