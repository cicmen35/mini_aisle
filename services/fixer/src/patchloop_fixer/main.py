from __future__ import annotations

from functools import partial

from patchloop_core.llm import build_llm_provider
from patchloop_core.logging import configure_logging
from patchloop_core.messages import FixRequested
from patchloop_core.runtime import build_runtime
from patchloop_core.settings import get_settings
from patchloop_core.worker import PostgresIdempotencyStore, RetryPolicy, Worker
from patchloop_fixer.handler import FixerDeps, handle_fix_requested


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    rt = build_runtime(settings)
    deps = FixerDeps(
        session_factory=rt.session_factory,
        artifacts=rt.artifacts,
        verify_queue=rt.queues.verify,
        llm=build_llm_provider(settings),
    )
    worker = Worker(
        queue=rt.queues.fix,
        message_type=FixRequested,
        handler=partial(handle_fix_requested, deps=deps),
        idempotency=PostgresIdempotencyStore(rt.session_factory),
        retry=RetryPolicy(max_attempts=settings.worker_max_attempts),
        wait_time_seconds=settings.worker_wait_time_seconds,
        max_messages=settings.worker_max_messages,
        visibility_timeout=settings.worker_visibility_timeout_seconds,
    )
    try:
        worker.run_forever()
    finally:
        rt.close()


if __name__ == "__main__":
    main()
