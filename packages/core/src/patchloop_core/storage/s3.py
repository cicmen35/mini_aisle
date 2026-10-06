from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from patchloop_core.aws import s3_client
from patchloop_core.settings import Settings
from patchloop_core.storage.base import ArtifactNotFoundError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class S3ArtifactStore:
    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self.bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> S3ArtifactStore:
        return cls(s3_client(settings), settings.artifacts_bucket)

    def put_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get_bytes(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise ArtifactNotFoundError(key) from exc
            raise
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                return False
            raise
        return True

    def ping(self) -> None:
        self._client.head_bucket(Bucket=self.bucket)
