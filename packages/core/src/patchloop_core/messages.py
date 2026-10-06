"""Message contracts for the three SQS queues.

    API ──ScanRequested──▶ scan queue ──▶ scanner
    scanner ──FixRequested──▶ fix queue ──▶ fixer          (one message per finding)
    fixer ──VerifyRequested──▶ verify queue ──▶ verifier   (one message per patch)

Rules every producer and consumer relies on:

* Messages are immutable facts, serialized as JSON with ``to_json()``.
* ``schema_version`` lets consumers reject messages they don't understand
  (they go to the DLQ instead of being silently mis-processed).
* ``idempotency_key`` is *deterministic* for a unit of work, so a redelivered or
  duplicated message has the same key and can be skipped. ``message_id`` is unique per send.
* Messages carry IDs and S3 keys, never large payloads (SQS limit is 256 KiB).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter

from patchloop_core.domain import ScannerName

SCHEMA_VERSION: Literal[1] = 1


def _now() -> datetime:
    return datetime.now(tz=UTC)


class _Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    message_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=_now)
    job_id: UUID
    # Propagated across hops so a whole job can be followed in the logs.
    correlation_id: UUID

    @property
    def idempotency_key(self) -> str:
        raise NotImplementedError

    def to_json(self) -> str:
        return self.model_dump_json()


class GitSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["git"] = "git"
    repo_url: HttpUrl
    ref: str = "HEAD"


class ArchiveSource(BaseModel):
    """A ``.tar.gz`` the API already uploaded to the artifacts bucket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["archive"] = "archive"
    s3_key: str


SourceRef = Annotated[GitSource | ArchiveSource, Field(discriminator="kind")]


class ScanRequested(_Message):
    type: Literal["scan.requested"] = "scan.requested"
    source: SourceRef
    scanners: tuple[ScannerName, ...] = (
        ScannerName.SEMGREP,
        ScannerName.BANDIT,
        ScannerName.PIP_AUDIT,
    )

    @property
    def idempotency_key(self) -> str:
        return f"scan:{self.job_id}"


class FixRequested(_Message):
    type: Literal["fix.requested"] = "fix.requested"
    finding_id: UUID
    # Immutable snapshot of the scanned source, written by the scanner, so the fixer and
    # verifier work on exactly the code that was scanned.
    source_snapshot_key: str

    @property
    def idempotency_key(self) -> str:
        return f"fix:{self.finding_id}"


class VerifyRequested(_Message):
    type: Literal["verify.requested"] = "verify.requested"
    finding_id: UUID
    patch_id: UUID
    patch_key: str
    source_snapshot_key: str

    @property
    def idempotency_key(self) -> str:
        return f"verify:{self.patch_id}"


AnyMessage = Annotated[ScanRequested | FixRequested | VerifyRequested, Field(discriminator="type")]
_any_message: TypeAdapter[ScanRequested | FixRequested | VerifyRequested] = TypeAdapter(AnyMessage)


def parse_message(body: str | bytes) -> ScanRequested | FixRequested | VerifyRequested:
    """Parse and validate any queue message. Raises ``pydantic.ValidationError`` on bad input."""
    return _any_message.validate_json(body)


class S3Keys:
    """Single source of truth for artifact key layout in the bucket."""

    @staticmethod
    def upload(job_id: UUID) -> str:
        return f"uploads/{job_id}/source.tar.gz"

    @staticmethod
    def source_snapshot(job_id: UUID) -> str:
        return f"snapshots/{job_id}/source.tar.gz"

    @staticmethod
    def scan_report(job_id: UUID, scanner: ScannerName) -> str:
        return f"reports/{job_id}/{scanner.value}.json"

    @staticmethod
    def patch(job_id: UUID, patch_id: UUID) -> str:
        return f"patches/{job_id}/{patch_id}.diff"

    @staticmethod
    def verification_log(job_id: UUID, patch_id: UUID) -> str:
        return f"verifications/{job_id}/{patch_id}.json"
