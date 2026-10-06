"""Public HTTP contract (request/response bodies). Changing these is an API change."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from patchloop_core.domain import FindingStatus, JobStatus, ScannerName, Severity, Verdict


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_url: HttpUrl = Field(examples=["https://github.com/example/vulnerable-app"])
    ref: str = Field(default="HEAD", max_length=255, pattern=r"^[\w./-]+$")
    scanners: list[ScannerName] = Field(default_factory=lambda: list(ScannerName))


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: JobStatus
    source_kind: str
    repo_url: str | None = None
    ref: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    finding_counts: dict[FindingStatus, int] = Field(default_factory=dict)


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    scanner: ScannerName
    rule_id: str
    severity: Severity
    file_path: str
    line_start: int
    line_end: int
    message: str
    status: FindingStatus


class PatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    finding_id: UUID
    model: str
    diff: str
    verdict: Verdict | None = None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)
