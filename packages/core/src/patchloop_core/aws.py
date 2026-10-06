"""boto3 client factory. ``aws_endpoint_url`` set means LocalStack; unset means real AWS."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from patchloop_core.settings import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_sqs import SQSClient

_BOTO_CONFIG = Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=5)


def sqs_client(settings: Settings) -> SQSClient:
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        config=_BOTO_CONFIG,
    )


def s3_client(settings: Settings) -> S3Client:
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        config=_BOTO_CONFIG.merge(Config(s3={"addressing_style": "path"})),
    )
