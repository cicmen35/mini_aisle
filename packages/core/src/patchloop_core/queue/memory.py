"""In-process queue with SQS-like semantics, for unit tests. Uses an injectable clock."""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from patchloop_core.queue.base import ReceivedMessage


@dataclass
class _Stored:
    message_id: str
    body: str
    visible_at: float
    receive_count: int = 0
    receipt_handle: str | None = None


class InMemoryQueue:
    """Simulates visibility timeouts, receive counts and redrive to a DLQ."""

    def __init__(
        self,
        name: str = "memory",
        *,
        dlq: InMemoryQueue | None = None,
        max_receive_count: int = 3,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.dlq = dlq
        self.max_receive_count = max_receive_count
        self._clock = clock
        self._messages: dict[str, _Stored] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def send(self, body: str, *, delay_seconds: int = 0) -> str:
        with self._lock:
            message_id = f"{self.name}-{next(self._ids)}"
            self._messages[message_id] = _Stored(
                message_id=message_id, body=body, visible_at=self._clock() + delay_seconds
            )
            return message_id

    def receive(
        self, *, max_messages: int = 1, wait_time_seconds: int = 0, visibility_timeout: int = 30
    ) -> list[ReceivedMessage]:
        now = self._clock()
        out: list[ReceivedMessage] = []
        with self._lock:
            for stored in list(self._messages.values()):
                if len(out) >= max_messages:
                    break
                if stored.visible_at > now:
                    continue
                if self.dlq is not None and stored.receive_count >= self.max_receive_count:
                    del self._messages[stored.message_id]
                    self.dlq.send(stored.body)
                    continue
                stored.receive_count += 1
                stored.visible_at = now + visibility_timeout
                stored.receipt_handle = f"{stored.message_id}#{stored.receive_count}"
                out.append(
                    ReceivedMessage(
                        body=stored.body,
                        message_id=stored.message_id,
                        receipt_handle=stored.receipt_handle,
                        receive_count=stored.receive_count,
                    )
                )
        return out

    def ack(self, message: ReceivedMessage) -> None:
        with self._lock:
            stored = self._messages.get(message.message_id)
            if stored is not None and stored.receipt_handle == message.receipt_handle:
                del self._messages[message.message_id]

    def change_visibility(self, message: ReceivedMessage, timeout_seconds: int) -> None:
        with self._lock:
            stored = self._messages.get(message.message_id)
            if stored is not None and stored.receipt_handle == message.receipt_handle:
                stored.visible_at = self._clock() + timeout_seconds

    def approximate_depth(self) -> int:
        now = self._clock()
        with self._lock:
            return sum(1 for m in self._messages.values() if m.visible_at <= now)

    def __len__(self) -> int:
        """All messages, visible or in flight."""
        return len(self._messages)
