"""Application logic behind the /v1 routes. Routes stay thin; everything interesting lives here.

Routes map ``None`` to 404 and ``NotImplementedError`` to 501.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from patchloop_api.schemas import CreateJobRequest, FindingResponse, JobResponse, PatchResponse
from patchloop_core.queue.base import QueueClient
from patchloop_core.settings import Settings
from patchloop_core.storage.base import ArtifactStore


@dataclass
class JobService:
    session: Session
    artifacts: ArtifactStore
    scan_queue: QueueClient
    settings: Settings

    def create_from_repo(
        self, request: CreateJobRequest, *, idempotency_key: str | None
    ) -> JobResponse:
        """TODO(simon): create a job for a git repository and enqueue ``ScanRequested``.

        - If ``idempotency_key`` was seen before, return the existing job (same response, no
          second message). This makes client retries safe.
        - Insert the job (status=queued) and publish ``ScanRequested(source=GitSource(...))``.
        - Think about the dual-write problem: the DB commit and the SQS send can't be atomic.
          Simplest acceptable answer: commit first, then send, and let the scanner tolerate a
          job that was re-enqueued. Better: transactional outbox (stretch goal).
        """
        raise NotImplementedError("TODO(simon): JobService.create_from_repo")

    def create_from_upload(
        self, *, filename: str, data: bytes, idempotency_key: str | None
    ) -> JobResponse:
        """TODO(simon): store ``data`` (a .tar.gz) at ``S3Keys.upload(job_id)``, then do the same
        as ``create_from_repo`` with ``ArchiveSource``. The route already enforced the size limit.
        """
        raise NotImplementedError("TODO(simon): JobService.create_from_upload")

    def get_job(self, job_id: UUID) -> JobResponse | None:
        """TODO(simon): load the job plus per-status finding counts (one query, GROUP BY)."""
        raise NotImplementedError("TODO(simon): JobService.get_job")

    def list_findings(self, job_id: UUID) -> list[FindingResponse] | None:
        """TODO(simon): ``None`` if the job doesn't exist, else its findings ordered by severity."""
        raise NotImplementedError("TODO(simon): JobService.list_findings")

    def get_latest_patch(self, finding_id: UUID) -> PatchResponse | None:
        """TODO(simon): newest patch for a finding, with the diff text loaded from S3."""
        raise NotImplementedError("TODO(simon): JobService.get_latest_patch")
