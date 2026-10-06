"""FastAPI app factory.

``create_app()`` builds real adapters from env settings on startup. Tests pass their own
``ApiContainer`` (in-memory queue/store) instead.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from patchloop_api.container import ApiContainer
from patchloop_api.routes import health, jobs
from patchloop_core import __version__
from patchloop_core.logging import configure_logging
from patchloop_core.settings import Settings, get_settings

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, container: ApiContainer | None = None) -> FastAPI:
    settings = settings or (container.settings if container else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        app.state.container = container or ApiContainer.from_settings(settings)
        log.info("api started", extra={"env": settings.env})
        try:
            yield
        finally:
            if owned:
                app.state.container.close()

    app = FastAPI(
        title="patchloop",
        version=__version__,
        summary="Find -> fix -> verify pipeline for security findings.",
        lifespan=lifespan,
    )
    if container is not None:
        app.state.container = container

    @app.exception_handler(NotImplementedError)
    async def not_implemented(_request: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={"detail": str(exc) or "not implemented"},
        )

    app.include_router(health.router)
    app.include_router(jobs.router)
    return app


def create_app_from_env() -> FastAPI:
    """Entry point for ``uvicorn --factory``."""
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    return create_app(settings)
