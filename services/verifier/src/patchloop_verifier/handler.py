from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from patchloop_core.domain import ScannerName
from patchloop_core.messages import VerifyRequested
from patchloop_core.scanning.base import ScannerRunner
from patchloop_core.storage.base import ArtifactStore


@dataclass
class VerifierDeps:
    session_factory: sessionmaker[Session]
    artifacts: ArtifactStore
    runners: dict[ScannerName, ScannerRunner]


def handle_verify_requested(message: VerifyRequested, deps: VerifierDeps) -> None:
    """TODO(simon): the verifier's unit of work.

    1. Extract the source snapshot into a temp dir; fingerprints "before" = the job's findings.
    2. ``apply_patch`` with the diff from ``message.patch_key``.
    3. Re-run the scanner that produced the finding (all of them if you prefer) on the patched
       tree and fingerprint the results; ``run_target_tests``.
    4. ``decide_verdict`` -> store a JSON log at ``S3Keys.verification_log``, record the verdict
       on the patch and set the finding to ``verified`` / ``rejected``.
    5. If this was the job's last open finding, mark the job ``completed``. Two verifiers can
       finish the last two findings concurrently - make this check race-free (row lock or a
       single conditional UPDATE).
    """
    raise NotImplementedError("TODO(simon): handle_verify_requested")
