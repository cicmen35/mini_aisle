"""Integration tests run on the host against the compose deps: `make deps-up` first."""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from patchloop_core.aws import s3_client, sqs_client
from patchloop_core.db.session import create_db_engine
from patchloop_core.queue import SqsQueue
from patchloop_core.settings import Settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return Settings(
        env="test",
        database_url=os.environ.get(  # type: ignore[arg-type]
            "PATCHLOOP_DATABASE_URL",
            "postgresql+psycopg://patchloop:patchloop@localhost:15432/patchloop",
        ),
        aws_endpoint_url=os.environ.get("PATCHLOOP_AWS_ENDPOINT_URL", "http://localhost:4566"),
    )


@pytest.fixture(scope="session")
def engine(settings: Settings) -> Iterator[Engine]:
    eng = create_db_engine(settings)
    yield eng
    eng.dispose()


@pytest.fixture
def temp_queue_with_dlq(settings: Settings) -> Iterator[tuple[SqsQueue, SqsQueue]]:
    """A throwaway queue + DLQ (maxReceiveCount=2), so tests never touch the real pipeline queues."""
    client = sqs_client(settings)
    name = f"it-{uuid4().hex[:8]}"
    dlq_url = client.create_queue(QueueName=f"{name}-dlq")["QueueUrl"]
    dlq_arn = client.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    url = client.create_queue(
        QueueName=name,
        Attributes={
            "RedrivePolicy": f'{{"deadLetterTargetArn":"{dlq_arn}","maxReceiveCount":"2"}}'
        },
    )["QueueUrl"]
    yield SqsQueue(client, url, name), SqsQueue(client, dlq_url, f"{name}-dlq")
    client.delete_queue(QueueUrl=url)
    client.delete_queue(QueueUrl=dlq_url)


@pytest.fixture(scope="session")
def s3(settings: Settings):  # type: ignore[no-untyped-def]
    return s3_client(settings)
