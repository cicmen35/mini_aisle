"""What Terraform must have provisioned in LocalStack for the services to work."""

from __future__ import annotations

import json
from typing import Any

import pytest

from patchloop_core.aws import sqs_client
from patchloop_core.settings import Settings

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("queue", ["scan", "fix", "verify"])
def test_queue_has_dlq_and_redrive_policy(settings: Settings, queue: str) -> None:
    client = sqs_client(settings)
    url = client.get_queue_url(QueueName=f"patchloop-{queue}-requests")["QueueUrl"]
    attrs = client.get_queue_attributes(QueueUrl=url, AttributeNames=["All"])["Attributes"]
    redrive = json.loads(attrs["RedrivePolicy"])
    assert redrive["deadLetterTargetArn"].endswith(f"patchloop-{queue}-requests-dlq")
    assert int(redrive["maxReceiveCount"]) >= 1
    assert attrs["ReceiveMessageWaitTimeSeconds"] == "20"
    assert attrs["SqsManagedSseEnabled"] == "true"

    dlq_url = client.get_queue_url(QueueName=f"patchloop-{queue}-requests-dlq")["QueueUrl"]
    dlq_attrs = client.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["All"])["Attributes"]
    allow = json.loads(dlq_attrs["RedriveAllowPolicy"])
    assert allow["redrivePermission"] == "byQueue"
    assert allow["sourceQueueArns"] == [attrs["QueueArn"]]


def test_artifacts_bucket_is_private_versioned_and_encrypted(settings: Settings, s3: Any) -> None:
    bucket = settings.artifacts_bucket
    assert s3.get_bucket_versioning(Bucket=bucket)["Status"] == "Enabled"
    enc = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]
    assert enc["Rules"][0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
    pab = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    assert all(pab.values())
