"""Generic queue consumer used by the scanner, fixer and verifier.

Split of responsibilities:

* ``Worker.run_forever`` (done): long-poll loop, graceful shutdown on SIGTERM/SIGINT, and a
  safety net so one bad message never kills the process.
* ``Worker.process`` (TODO(simon)): what happens to *one* message - parse, dedupe, call the
  handler, ack, retry with backoff or give up. This is where at-least-once delivery,
  idempotency and DLQs become real.
* Handlers (TODO(simon), one per service): the business logic for one message type.
"""

from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType
from typing import Protocol

from pydantic import BaseModel

from patchloop_core.queue.base import QueueClient, ReceivedMessage

log = logging.getLogger(__name__)


class TransientError(Exception):
    """Retry later (dependency down, timeout, throttling). The message must not be acked."""


class PermanentError(Exception):
    """Retrying cannot help (invalid input, patch rejected). Record the failure and ack."""


class IdempotencyStore(Protocol):
    """Remembers which units of work (``message.idempotency_key``) were already completed."""

    def is_processed(self, key: str) -> bool: ...

    def mark_processed(self, key: str) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self.keys: set[str] = set()

    def is_processed(self, key: str) -> bool:
        return key in self.keys

    def mark_processed(self, key: str) -> None:
        self.keys.add(key)


class PostgresIdempotencyStore:
    """Inbox table (``processed_messages``) so dedupe survives restarts and scales across replicas.

    TODO(simon): implement with the ``processed_messages`` model. ``mark_processed`` should be an
    ``INSERT ... ON CONFLICT DO NOTHING``; ideally it runs in the *same transaction* as the
    handler's writes, so "work done" and "marked done" can't diverge.
    """

    def __init__(self, session_factory: Callable[[], object]) -> None:
        self._session_factory = session_factory

    def is_processed(self, key: str) -> bool:
        raise NotImplementedError("TODO(simon): PostgresIdempotencyStore.is_processed")

    def mark_processed(self, key: str) -> None:
        raise NotImplementedError("TODO(simon): PostgresIdempotencyStore.mark_processed")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 5
    max_delay_seconds: int = 300

    def backoff_seconds(self, attempt: int) -> int:
        """Delay before attempt ``attempt + 1``. Exponential backoff, capped.

        TODO(simon): implement (e.g. base * 2 ** (attempt - 1), capped at max). Bonus: add jitter
        and explain in the interview why jitter matters (thundering herd).
        """
        raise NotImplementedError("TODO(simon): RetryPolicy.backoff_seconds")


class Worker[M: BaseModel]:
    def __init__(
        self,
        *,
        queue: QueueClient,
        message_type: type[M],
        handler: Callable[[M], None],
        idempotency: IdempotencyStore,
        retry: RetryPolicy | None = None,
        wait_time_seconds: int = 20,
        max_messages: int = 5,
        visibility_timeout: int = 120,
    ) -> None:
        self.queue = queue
        self.message_type = message_type
        self.handler = handler
        self.idempotency = idempotency
        self.retry = retry or RetryPolicy()
        self.wait_time_seconds = wait_time_seconds
        self.max_messages = max_messages
        self.visibility_timeout = visibility_timeout
        self._stop = threading.Event()

    def process(self, received: ReceivedMessage) -> None:
        """Handle exactly one received message. Must never raise for expected failure modes.

        TODO(simon): implement. Expected behaviour (see tests/unit/test_worker_process.py):

        1. Parse ``received.body`` into ``self.message_type``. Invalid -> log and leave it
           un-acked so the redrive policy moves it to the DLQ (poison message).
        2. If ``self.idempotency.is_processed(msg.idempotency_key)``: ack and return (duplicate).
        3. Call ``self.handler(msg)``.
           - success -> ``mark_processed`` then ``ack``.
           - ``TransientError`` -> don't ack; ``change_visibility`` to
             ``self.retry.backoff_seconds(received.receive_count)`` so it retries later.
           - ``PermanentError`` -> mark processed and ack (the handler recorded the failure).
           - any other exception -> treat as transient.
        4. Log with ``message_id``, ``job_id``, ``correlation_id`` and ``receive_count``.
        """
        raise NotImplementedError("TODO(simon): Worker.process")

    def run_once(self) -> int:
        """Receive one batch and process it. Returns the number of messages received."""
        batch = self.queue.receive(
            max_messages=self.max_messages,
            wait_time_seconds=self.wait_time_seconds,
            visibility_timeout=self.visibility_timeout,
        )
        for received in batch:
            if self._stop.is_set():
                # Not acked: becomes visible again after the visibility timeout.
                break
            try:
                self.process(received)
            except Exception:
                log.exception(
                    "unhandled error processing message; leaving it for redelivery",
                    extra={"queue": self.queue.name, "message_id": received.message_id},
                )
        return len(batch)

    def run_forever(self) -> None:
        self._install_signal_handlers()
        log.info("worker started", extra={"queue": self.queue.name})
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                log.exception("receive failed; backing off", extra={"queue": self.queue.name})
                self._stop.wait(5)
        log.info("worker stopped", extra={"queue": self.queue.name})

    def stop(self) -> None:
        self._stop.set()

    def _install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return

        def _handle(signum: int, _frame: FrameType | None) -> None:
            log.info("shutdown signal received", extra={"signal": signum})
            self.stop()

        signal.signal(signal.SIGTERM, _handle)
        signal.signal(signal.SIGINT, _handle)
