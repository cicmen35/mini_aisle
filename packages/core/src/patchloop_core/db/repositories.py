"""Data-access functions. Keep SQL here so API routes and worker handlers stay thin.

TODO(simon): once ``models.py`` exists, add query functions that the API services and the
worker handlers call, each taking a ``Session`` as the first argument, for example:

    create_job(session, *, source, idempotency_key) -> Job
    get_job(session, job_id) -> Job | None
    get_job_by_idempotency_key(session, key) -> Job | None
    set_job_status(session, job_id, status, *, error=None) -> None
    add_findings(session, job_id, findings) -> list[Finding]   # ON CONFLICT (job_id, fingerprint) DO NOTHING
    list_findings(session, job_id) -> list[Finding]
    add_patch(session, finding_id, *, s3_key, model) -> Patch
    record_verdict(session, patch_id, verdict, *, verification_key) -> None

Tips: use ``sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing`` for idempotent
inserts, and ``select(...).with_for_update(skip_locked=True)`` if you ever poll the DB as a queue.
"""
