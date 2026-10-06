from __future__ import annotations

from functools import partial

from patchloop_core.logging import configure_logging
from patchloop_core.messages import VerifyRequested
from patchloop_core.runtime import build_runtime
from patchloop_core.scanning.runners import default_runners
from patchloop_core.settings import get_settings
from patchloop_core.worker import PostgresIdempotencyStore, RetryPolicy, Worker
from patchloop_verifier.handler import VerifierDeps, handle_verify_requested


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    rt = build_runtime(settings)
    deps = VerifierDeps(
        session_factory=rt.session_factory,
        artifacts=rt.artifacts,
        runners=default_runners(
            semgrep_config=settings.scanner_semgrep_config,
            timeout_seconds=settings.scanner_timeout_seconds,
        ),
    )
    worker = Worker(
        queue=rt.queues.verify,
        message_type=VerifyRequested,
        handler=partial(handle_verify_requested, deps=deps),
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
