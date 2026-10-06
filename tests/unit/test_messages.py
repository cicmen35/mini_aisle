from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from patchloop_core.domain import ScannerName
from patchloop_core.messages import (
    ArchiveSource,
    FixRequested,
    GitSource,
    S3Keys,
    ScanRequested,
    VerifyRequested,
    parse_message,
)


def _scan() -> ScanRequested:
    job_id = uuid4()
    return ScanRequested(
        job_id=job_id,
        correlation_id=job_id,
        source=GitSource(repo_url="https://github.com/example/app"),  # type: ignore[arg-type]
    )


def test_round_trip_through_json_keeps_type_and_fields() -> None:
    msg = _scan()
    parsed = parse_message(msg.to_json())
    assert isinstance(parsed, ScanRequested)
    assert parsed == msg


def test_idempotency_key_is_stable_across_redeliveries() -> None:
    msg = _scan()
    resent = msg.model_copy(update={"message_id": uuid4()})
    assert resent.message_id != msg.message_id
    assert resent.idempotency_key == msg.idempotency_key == f"scan:{msg.job_id}"


def test_keys_per_message_type() -> None:
    job, finding, patch = uuid4(), uuid4(), uuid4()
    fix = FixRequested(job_id=job, correlation_id=job, finding_id=finding, source_snapshot_key="k")
    verify = VerifyRequested(
        job_id=job,
        correlation_id=job,
        finding_id=finding,
        patch_id=patch,
        patch_key="p",
        source_snapshot_key="k",
    )
    assert fix.idempotency_key == f"fix:{finding}"
    assert verify.idempotency_key == f"verify:{patch}"


def test_archive_source_discriminator() -> None:
    job = uuid4()
    msg = ScanRequested(
        job_id=job,
        correlation_id=job,
        source=ArchiveSource(s3_key=S3Keys.upload(job)),
        scanners=(ScannerName.BANDIT,),
    )
    parsed = parse_message(msg.to_json())
    assert isinstance(parsed, ScanRequested)
    assert isinstance(parsed.source, ArchiveSource)


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        '{"type": "scan.requested"}',
        '{"type": "unknown.type", "job_id": "00000000-0000-0000-0000-000000000000"}',
    ],
)
def test_poison_messages_fail_validation(body: str) -> None:
    with pytest.raises(ValidationError):
        parse_message(body)


def test_unknown_schema_version_is_rejected() -> None:
    payload = _scan().model_dump(mode="json")
    payload["schema_version"] = 2
    with pytest.raises(ValidationError):
        ScanRequested.model_validate(payload)


def test_messages_are_immutable() -> None:
    msg = _scan()
    with pytest.raises(ValidationError):
        msg.job_id = uuid4()  # type: ignore[misc]
