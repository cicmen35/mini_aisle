from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status

from patchloop_api.deps import ContainerDep, JobServiceDep
from patchloop_api.schemas import CreateJobRequest, FindingResponse, JobResponse, PatchResponse

router = APIRouter(prefix="/v1", tags=["jobs"])

IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)]
ALLOWED_UPLOAD_TYPES = {
    "application/gzip",
    "application/x-gzip",
    "application/x-tar",
    "application/octet-stream",
}


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    body: CreateJobRequest, service: JobServiceDep, idempotency_key: IdempotencyKey = None
) -> JobResponse:
    return service.create_from_repo(body, idempotency_key=idempotency_key)


@router.post("/jobs/upload", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job_from_upload(
    container: ContainerDep,
    service: JobServiceDep,
    file: Annotated[UploadFile, File(description="Source code as .tar.gz")],
    idempotency_key: IdempotencyKey = None,
) -> JobResponse:
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "upload a .tar.gz archive")
    limit = container.settings.api_max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"archive exceeds {limit} bytes")
    return service.create_from_upload(
        filename=file.filename or "source.tar.gz", data=data, idempotency_key=idempotency_key
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, service: JobServiceDep) -> JobResponse:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return job


@router.get("/jobs/{job_id}/findings", response_model=list[FindingResponse])
def list_findings(job_id: UUID, service: JobServiceDep) -> list[FindingResponse]:
    findings = service.list_findings(job_id)
    if findings is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return findings


@router.get("/findings/{finding_id}/patch", response_model=PatchResponse)
def get_patch(finding_id: UUID, service: JobServiceDep) -> PatchResponse:
    patch = service.get_latest_patch(finding_id)
    if patch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no patch for this finding")
    return patch
