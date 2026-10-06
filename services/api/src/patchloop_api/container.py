"""Dependencies the API needs, built once per process and stored on ``app.state``."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from patchloop_core.queue.base import QueueClient
from patchloop_core.runtime import build_runtime
from patchloop_core.settings import Settings
from patchloop_core.storage.base import ArtifactStore


@dataclass
class ApiContainer:
    settings: Settings
    artifacts: ArtifactStore
    scan_queue: QueueClient
    engine: Engine | None = None
    session_factory: sessionmaker[Session] | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> ApiContainer:
        rt = build_runtime(settings)
        return cls(
            settings=settings,
            artifacts=rt.artifacts,
            scan_queue=rt.queues.scan,
            engine=rt.engine,
            session_factory=rt.session_factory,
        )

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
