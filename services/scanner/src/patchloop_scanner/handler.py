from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from patchloop_core.domain import ScannerName
from patchloop_core.messages import ScanRequested
from patchloop_core.queue.base import QueueClient
from patchloop_core.scanning.base import ScannerRunner
from patchloop_core.storage.base import ArtifactStore


@dataclass
class ScannerDeps:
    session_factory: sessionmaker[Session]
    artifacts: ArtifactStore
    fix_queue: QueueClient
    runners: dict[ScannerName, ScannerRunner]


def handle_scan_requested(message: ScanRequested, deps: ScannerDeps) -> None:
    """TODO(simon): the scanner's unit of work.

    1. Mark the job ``scanning``.
    2. Materialise the source in a fresh temp dir: ``clone_repo`` for ``GitSource``, or
       ``safe_extract_tarball(artifacts.get_bytes(source.s3_key))`` for ``ArchiveSource``.
    3. Upload an immutable snapshot (``make_tarball``) to ``S3Keys.source_snapshot(job_id)``.
    4. Run each requested runner; store ``report.raw_output`` at ``S3Keys.scan_report``.
       A failing tool shouldn't fail the whole job - decide and justify.
    5. Persist findings with a ``finding_fingerprint`` (dedupe on redelivery!).
    6. Publish one ``FixRequested`` per *new* finding (same ``correlation_id``), then mark the
       job ``fixing`` (or ``completed`` if there were no findings).

    Raise ``TransientError`` for retryable problems (S3/DB down), ``PermanentError`` for bad
    input (clone fails, archive rejected) after recording the job as ``failed``.
    """
    raise NotImplementedError("TODO(simon): handle_scan_requested")
