from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from patchloop_core.llm.base import LLMProvider
from patchloop_core.messages import FixRequested
from patchloop_core.queue.base import QueueClient
from patchloop_core.storage.base import ArtifactStore


@dataclass
class FixerDeps:
    session_factory: sessionmaker[Session]
    artifacts: ArtifactStore
    verify_queue: QueueClient
    llm: LLMProvider


def handle_fix_requested(message: FixRequested, deps: FixerDeps) -> None:
    """TODO(simon): the fixer's unit of work.

    1. Load the finding; download + extract the source snapshot; read the affected file.
    2. ``build_fix_prompt`` -> ``deps.llm.complete`` -> ``extract_unified_diff`` ->
       ``validate_patch_paths``.
    3. Store the diff at ``S3Keys.patch``, insert a ``patches`` row, set the finding to
       ``fix_proposed`` and publish ``VerifyRequested``.
    4. ``LLMError(retryable=True)`` -> ``TransientError``. An unusable answer
       (``InvalidPatchError``) -> finding ``fix_failed`` + ``PermanentError``. Optional: retry
       the LLM once with the validation error in the prompt.
    """
    raise NotImplementedError("TODO(simon): handle_fix_requested")
