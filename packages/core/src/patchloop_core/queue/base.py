"""Queue client contract. Workers and the API only depend on this, never on boto3 directly.

Semantics mirror SQS standard queues (at-least-once delivery):

* ``receive`` hides returned messages for ``visibility_timeout`` seconds. If the consumer
  doesn't ``ack`` in time, the message becomes visible again and is redelivered.
* ``receive_count`` tells how many times a message was delivered. After ``maxReceiveCount``
  deliveries the queue's redrive policy moves it to the dead-letter queue.
* Ordering is not guaranteed and duplicates are possible, so consumers must be idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ReceivedMessage:
    body: str
    message_id: str
    receipt_handle: str
    receive_count: int = 1
    attributes: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class QueueClient(Protocol):
    """One logical queue (e.g. the scan queue)."""

    name: str

    def send(self, body: str, *, delay_seconds: int = 0) -> str:
        """Enqueue ``body``; returns the broker message id."""
        ...

    def receive(
        self, *, max_messages: int = 1, wait_time_seconds: int = 0, visibility_timeout: int = 30
    ) -> list[ReceivedMessage]:
        """Long-poll for up to ``max_messages``. Returns ``[]`` when nothing arrived."""
        ...

    def ack(self, message: ReceivedMessage) -> None:
        """Delete a successfully processed message so it is never redelivered."""
        ...

    def change_visibility(self, message: ReceivedMessage, timeout_seconds: int) -> None:
        """Extend processing time (heartbeat) or, with a small value, schedule a retry."""
        ...

    def approximate_depth(self) -> int:
        """Visible messages waiting. Used by readiness checks and autoscaling demos."""
        ...
