"""Thin boto3 adapter implementing ``QueueClient`` for SQS / LocalStack."""

from __future__ import annotations

from typing import TYPE_CHECKING

from patchloop_core.aws import sqs_client
from patchloop_core.queue.base import ReceivedMessage
from patchloop_core.settings import Settings

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient


class SqsQueue:
    def __init__(self, client: SQSClient, queue_url: str, name: str | None = None) -> None:
        self._client = client
        self.queue_url = queue_url
        self.name = name or queue_url.rsplit("/", 1)[-1]

    @classmethod
    def from_name(cls, settings: Settings, queue_name: str) -> SqsQueue:
        client = sqs_client(settings)
        url = client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        return cls(client, url, queue_name)

    def send(self, body: str, *, delay_seconds: int = 0) -> str:
        resp = self._client.send_message(
            QueueUrl=self.queue_url, MessageBody=body, DelaySeconds=delay_seconds
        )
        return resp["MessageId"]

    def receive(
        self, *, max_messages: int = 1, wait_time_seconds: int = 0, visibility_timeout: int = 30
    ) -> list[ReceivedMessage]:
        resp = self._client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=visibility_timeout,
            MessageSystemAttributeNames=["ApproximateReceiveCount", "SentTimestamp"],
        )
        return [
            ReceivedMessage(
                body=m["Body"],
                message_id=m["MessageId"],
                receipt_handle=m["ReceiptHandle"],
                receive_count=int(m.get("Attributes", {}).get("ApproximateReceiveCount", "1")),
                attributes={str(k): v for k, v in m.get("Attributes", {}).items()},
            )
            for m in resp.get("Messages", [])
        ]

    def ack(self, message: ReceivedMessage) -> None:
        self._client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=message.receipt_handle)

    def change_visibility(self, message: ReceivedMessage, timeout_seconds: int) -> None:
        self._client.change_message_visibility(
            QueueUrl=self.queue_url,
            ReceiptHandle=message.receipt_handle,
            VisibilityTimeout=timeout_seconds,
        )

    def approximate_depth(self) -> int:
        attrs = self._client.get_queue_attributes(
            QueueUrl=self.queue_url, AttributeNames=["ApproximateNumberOfMessages"]
        )["Attributes"]
        return int(attrs.get("ApproximateNumberOfMessages", "0"))
