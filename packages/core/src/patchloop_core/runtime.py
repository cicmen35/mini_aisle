"""Wires concrete adapters (Postgres, SQS, S3) from ``Settings``. Used by every service's main()."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from patchloop_core.db.session import create_db_engine, create_session_factory
from patchloop_core.queue.base import QueueClient
from patchloop_core.queue.sqs import SqsQueue
from patchloop_core.settings import Settings
from patchloop_core.storage.base import ArtifactStore
from patchloop_core.storage.s3 import S3ArtifactStore


@dataclass
class Queues:
    scan: QueueClient
    fix: QueueClient
    verify: QueueClient


@dataclass
class Runtime:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    artifacts: ArtifactStore
    queues: Queues

    def close(self) -> None:
        self.engine.dispose()


def build_runtime(settings: Settings) -> Runtime:
    engine = create_db_engine(settings)
    return Runtime(
        settings=settings,
        engine=engine,
        session_factory=create_session_factory(engine),
        artifacts=S3ArtifactStore.from_settings(settings),
        queues=Queues(
            scan=SqsQueue.from_name(settings, settings.scan_queue_name),
            fix=SqsQueue.from_name(settings, settings.fix_queue_name),
            verify=SqsQueue.from_name(settings, settings.verify_queue_name),
        ),
    )
