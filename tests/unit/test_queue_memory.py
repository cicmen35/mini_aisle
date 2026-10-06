"""The in-memory queue must behave like SQS, since worker tests rely on it."""

from __future__ import annotations

from patchloop_core.queue import InMemoryQueue, QueueClient


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_implements_protocol() -> None:
    assert isinstance(InMemoryQueue(), QueueClient)


def test_received_message_is_invisible_until_timeout() -> None:
    clock = FakeClock()
    q = InMemoryQueue(clock=clock)
    q.send("hello")
    [msg] = q.receive(visibility_timeout=30)
    assert msg.receive_count == 1
    assert q.receive() == []
    clock.now = 31
    [again] = q.receive()
    assert again.body == "hello"
    assert again.receive_count == 2


def test_ack_deletes() -> None:
    q = InMemoryQueue()
    q.send("x")
    [msg] = q.receive()
    q.ack(msg)
    assert len(q) == 0


def test_stale_receipt_handle_cannot_ack() -> None:
    clock = FakeClock()
    q = InMemoryQueue(clock=clock)
    q.send("x")
    [first] = q.receive(visibility_timeout=1)
    clock.now = 2
    [_second] = q.receive(visibility_timeout=10)
    q.ack(first)
    assert len(q) == 1


def test_redrive_to_dlq_after_max_receive_count() -> None:
    clock = FakeClock()
    dlq = InMemoryQueue("dlq", clock=clock)
    q = InMemoryQueue("main", dlq=dlq, max_receive_count=3, clock=clock)
    q.send("poison")
    for _ in range(3):
        assert len(q.receive(visibility_timeout=0)) == 1
    assert q.receive(visibility_timeout=0) == []
    assert len(q) == 0
    assert [m.body for m in dlq.receive()] == ["poison"]


def test_change_visibility_delays_retry() -> None:
    clock = FakeClock()
    q = InMemoryQueue(clock=clock)
    q.send("x")
    [msg] = q.receive(visibility_timeout=300)
    q.change_visibility(msg, 5)
    clock.now = 6
    assert len(q.receive()) == 1


def test_delay_seconds_and_depth() -> None:
    clock = FakeClock()
    q = InMemoryQueue(clock=clock)
    q.send("later", delay_seconds=10)
    q.send("now")
    assert q.approximate_depth() == 1
    clock.now = 11
    assert q.approximate_depth() == 2
