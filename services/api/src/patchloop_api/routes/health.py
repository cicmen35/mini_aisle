"""Liveness vs readiness: Kubernetes restarts on failed liveness, stops routing on failed readiness."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Response, status

from patchloop_api.deps import ContainerDep
from patchloop_api.schemas import HealthResponse
from patchloop_core.db.session import ping

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


@router.get("/healthz", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
def readiness(container: ContainerDep, response: Response) -> HealthResponse:
    checks: dict[str, str] = {}

    if container.engine is None:
        checks["database"] = "not configured"
    else:
        try:
            ping(container.engine)
            checks["database"] = "ok"
        except Exception as exc:
            log.warning("readiness: database check failed", exc_info=exc)
            checks["database"] = "error"

    try:
        container.scan_queue.approximate_depth()
        checks["scan_queue"] = "ok"
    except Exception as exc:
        log.warning("readiness: queue check failed", exc_info=exc)
        checks["scan_queue"] = "error"

    ok = all(v == "ok" for v in checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="ok" if ok else "degraded", checks=checks)
