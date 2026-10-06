"""End-to-end definition of done, against the full compose stack (`make up`, mock LLM).

Each test xfails while the API answers 501 (TODO(simon)), and becomes a real check once the
services are implemented.
"""

from __future__ import annotations

import io
import os
import tarfile
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from patchloop_core.domain import FindingStatus, JobStatus

pytestmark = [pytest.mark.e2e, pytest.mark.todo]

API = os.environ.get("PATCHLOOP_API_URL", "http://localhost:8420")
DEMO_APP = Path(__file__).resolve().parents[2] / "demo-targets" / "vulnerable-app"


@pytest.fixture(scope="module")
def api() -> httpx.Client:
    client = httpx.Client(base_url=API, timeout=10)
    try:
        client.get("/healthz").raise_for_status()
    except httpx.HTTPError:
        pytest.skip(f"API not reachable at {API} (make up)")
    return client


def _check(resp: httpx.Response) -> Any:
    if resp.status_code == 501:
        raise NotImplementedError(resp.json()["detail"])
    resp.raise_for_status()
    return resp.json()


def _demo_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(DEMO_APP, arcname=".", filter=lambda ti: None if "__pycache__" in ti.name else ti)
    return buf.getvalue()


def _wait_for_terminal(api: httpx.Client, job_id: str, timeout: float = 300) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = _check(api.get(f"/v1/jobs/{job_id}"))
        if JobStatus(job["status"]).is_terminal:
            return job  # type: ignore[no-any-return]
        time.sleep(2)
    pytest.fail(f"job {job_id} not finished after {timeout}s")


def test_upload_demo_app_flows_through_scan_fix_verify(api: httpx.Client) -> None:
    job = _check(
        api.post(
            "/v1/jobs/upload",
            files={"file": ("demo.tar.gz", _demo_tarball(), "application/gzip")},
        )
    )
    assert job["status"] == JobStatus.QUEUED

    job = _wait_for_terminal(api, job["id"])
    assert job["status"] == JobStatus.COMPLETED

    findings = _check(api.get(f"/v1/jobs/{job['id']}/findings"))
    files = {f["file_path"] for f in findings}
    # All four planted bugs are found.
    assert {
        "vulnapp/users.py",
        "vulnapp/reports.py",
        "vulnapp/session.py",
        "vulnapp/network.py",
    } <= files
    # Every finding went through fixer + verifier and ended in a terminal state.
    assert all(FindingStatus(f["status"]).is_terminal for f in findings)


def test_resubmitting_with_same_idempotency_key_returns_same_job(api: httpx.Client) -> None:
    body = {"repo_url": "https://github.com/cicmen35/does-not-matter"}
    headers = {"Idempotency-Key": f"e2e-{time.time_ns()}"}
    first = _check(api.post("/v1/jobs", json=body, headers=headers))
    second = _check(api.post("/v1/jobs", json=body, headers=headers))
    assert first["id"] == second["id"]


def test_unknown_job_is_404(api: httpx.Client) -> None:
    resp = api.get("/v1/jobs/00000000-0000-0000-0000-000000000000")
    if resp.status_code == 501:
        raise NotImplementedError(resp.json()["detail"])
    assert resp.status_code == 404
