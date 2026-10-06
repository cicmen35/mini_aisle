"""FastAPI dependency providers. Override these in tests with ``app.dependency_overrides``."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from patchloop_api.container import ApiContainer
from patchloop_api.services.jobs import JobService
from patchloop_core.db.session import session_scope


def get_container(request: Request) -> ApiContainer:
    container: ApiContainer = request.app.state.container
    return container


ContainerDep = Annotated[ApiContainer, Depends(get_container)]


def get_session(container: ContainerDep) -> Iterator[Session]:
    if container.session_factory is None:
        raise RuntimeError("database is not configured")
    with session_scope(container.session_factory) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_job_service(container: ContainerDep, session: SessionDep) -> JobService:
    return JobService(
        session=session,
        artifacts=container.artifacts,
        scan_queue=container.scan_queue,
        settings=container.settings,
    )


JobServiceDep = Annotated[JobService, Depends(get_job_service)]
