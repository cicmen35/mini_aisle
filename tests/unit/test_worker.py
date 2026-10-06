"""Worker loop plumbing (passing) + the contract for ``Worker.process`` (TODO(simon))."""

from __future__ import annotations

from uuid import uuid4

import pytest

from patchloop_core.messages import FixRequested
from patchloop_core.queue import InMemoryQueue
from patchloop_core.worker import (
    InMemoryIdempotencyStore,
    PermanentError,
    RetryPolicy,
    TransientError,
    Worker,
)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _fix_message() -> FixRequested:
    job = uuid4()
    return FixRequested(job_id=job, correlation_id=job, finding_id=uuid4(), source_snapshot_key="s")


class Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[FixRequested] = []
        self.error = error

    def __call__(self, msg: FixRequested) -> None:
        self.calls.append(msg)
        if self.error is not None:
            raise self.error


def _worker(
    queue: InMemoryQueue, handler: Recorder, store: InMemoryIdempotencyStore | None = None
) -> Worker[FixRequested]:
    return Worker(
        queue=queue,
        message_type=FixRequested,
        handler=handler,
        idempotency=store or InMemoryIdempotencyStore(),
        retry=RetryPolicy(max_attempts=3, base_delay_seconds=5, max_delay_seconds=60),
        wait_time_seconds=0,
        visibility_timeout=30,
    )


# ---- plumbing ---------------------------------------------------------------------------


def test_run_once_survives_errors_in_process_and_leaves_message_for_redelivery() -> None:
    q = InMemoryQueue()
    q.send(_fix_message().to_json())
    worker = _worker(q, Recorder())
    assert worker.run_once() == 1  # process() raising must not crash the loop
    assert len(q) == 1


def test_stop_ends_run_forever() -> None:
    q = InMemoryQueue()
    worker = _worker(q, Recorder())
    worker.stop()
    worker.run_forever()


# ---- TODO(simon): Worker.process ----------------------------------------------------------


@pytest.mark.todo
def test_success_acks_and_marks_processed() -> None:
    q, store, handler = InMemoryQueue(), InMemoryIdempotencyStore(), Recorder()
    msg = _fix_message()
    q.send(msg.to_json())
    worker = _worker(q, handler, store)
    [received] = q.receive()
    worker.process(received)
    assert [m.message_id for m in handler.calls] == [msg.message_id]
    assert len(q) == 0
    assert store.is_processed(msg.idempotency_key)


@pytest.mark.todo
def test_duplicate_delivery_runs_handler_once() -> None:
    q, store, handler = InMemoryQueue(), InMemoryIdempotencyStore(), Recorder()
    msg = _fix_message()
    q.send(msg.to_json())
    q.send(msg.model_copy(update={"message_id": uuid4()}).to_json())  # same unit of work
    worker = _worker(q, handler, store)
    for received in q.receive(max_messages=10):
        worker.process(received)
    assert len(handler.calls) == 1
    assert len(q) == 0


@pytest.mark.todo
def test_transient_error_schedules_retry_with_backoff() -> None:
    clock = Clock()
    q = InMemoryQueue(clock=clock)
    q.send(_fix_message().to_json())
    worker = _worker(q, Recorder(TransientError("db down")))
    [received] = q.receive(visibility_timeout=300)
    worker.process(received)
    assert len(q) == 1, "must not be acked"
    clock.now = worker.retry.backoff_seconds(1) + 0.1
    assert len(q.receive()) == 1, "visible again after backoff, not after 300s"


@pytest.mark.todo
def test_permanent_error_acks() -> None:
    q = InMemoryQueue()
    q.send(_fix_message().to_json())
    worker = _worker(q, Recorder(PermanentError("bad input")))
    [received] = q.receive()
    worker.process(received)
    assert len(q) == 0


@pytest.mark.todo
def test_poison_message_ends_up_in_dlq() -> None:
    dlq = InMemoryQueue("dlq")
    q = InMemoryQueue("main", dlq=dlq, max_receive_count=3)
    q.send("{not valid json")
    worker = _worker(q, Recorder())
    for _ in range(3):
        for received in q.receive(visibility_timeout=0):
            worker.process(received)
    assert q.receive(visibility_timeout=0) == []
    assert len(dlq) == 1


@pytest.mark.todo
@pytest.mark.parametrize(("attempt", "expected"), [(1, 5), (2, 10), (3, 20), (10, 60)])
def test_backoff_is_exponential_and_capped(attempt: int, expected: int) -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=5, max_delay_seconds=60)
    # Allow jitter of up to +-50% if you add it.
    assert expected * 0.5 <= policy.backoff_seconds(attempt) <= expected * 1.5
