from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from patchloop_api.app import create_app
from patchloop_api.container import ApiContainer
from patchloop_api.deps import get_job_service
from patchloop_api.services.jobs import JobService
from patchloop_core.queue import InMemoryQueue
from patchloop_core.settings import Settings
from patchloop_core.storage import InMemoryArtifactStore


@pytest.fixture
def container() -> ApiContainer:
    return ApiContainer(
        settings=Settings(env="test", api_max_upload_bytes=1024),
        artifacts=InMemoryArtifactStore(),
        scan_queue=InMemoryQueue("scan"),
    )


@pytest.fixture
def client(container: ApiContainer) -> Iterator[TestClient]:
    app = create_app(container=container)

    def service_without_db() -> JobService:
        return JobService(
            session=None,  # type: ignore[arg-type]
            artifacts=container.artifacts,
            scan_queue=container.scan_queue,
            settings=container.settings,
        )

    app.dependency_overrides[get_job_service] = service_without_db
    with TestClient(app) as c:
        yield c


def test_liveness(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok", "checks": {}}


def test_readiness_reports_missing_database(client: TestClient) -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["checks"] == {"database": "not configured", "scan_queue": "ok"}


def test_openapi_documents_the_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/v1/jobs",
        "/v1/jobs/upload",
        "/v1/jobs/{job_id}",
        "/v1/jobs/{job_id}/findings",
        "/v1/findings/{finding_id}/patch",
    } <= set(paths)


def test_request_validation_happens_before_service(client: TestClient) -> None:
    assert client.post("/v1/jobs", json={"repo_url": "not a url"}).status_code == 422
    assert (
        client.post("/v1/jobs", json={"repo_url": "https://x.io/r", "ref": "a; rm -rf"}).status_code
        == 422
    )
    assert client.get("/v1/jobs/not-a-uuid").status_code == 422


def test_upload_limits_are_enforced(client: TestClient) -> None:
    too_big = client.post(
        "/v1/jobs/upload", files={"file": ("s.tar.gz", b"x" * 2048, "application/gzip")}
    )
    assert too_big.status_code == 413
    wrong_type = client.post("/v1/jobs/upload", files={"file": ("s.txt", b"x", "text/plain")})
    assert wrong_type.status_code == 415


def test_unimplemented_service_returns_501(client: TestClient) -> None:
    resp = client.get(f"/v1/jobs/{uuid4()}")
    assert resp.status_code == 501
    assert "TODO(simon)" in resp.json()["detail"]


# ---- What "done" means for the API service (TODO(simon)) ------------------------------------
# These run against an in-memory queue/store and need a DB session, so they live in
# tests/integration/test_api_jobs.py. The unit-level contract is below.


@pytest.mark.todo
def test_create_job_enqueues_scan_request(client: TestClient, container: ApiContainer) -> None:
    resp = client.post("/v1/jobs", json={"repo_url": "https://github.com/example/app"})
    if resp.status_code == 501:
        raise NotImplementedError(resp.json()["detail"])
    assert resp.status_code == 202
    assert container.scan_queue.approximate_depth() == 1
