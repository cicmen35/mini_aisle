"""ORM models. Import every model here so Alembic autogenerate can see it.

TODO(simon): define the tables below with SQLAlchemy 2.0 typed mappings
(``Mapped[...]`` / ``mapped_column``), then run ``make db-revision m="create core tables"``
and review the generated migration before ``make migrate``.

Suggested schema (adapt freely, but keep the API contract in ``patchloop_api.schemas``):

``jobs``
    id UUID pk, status (JobStatus) indexed, source_kind ("git" | "archive"), repo_url, ref,
    upload_key, idempotency_key UNIQUE NULL (from the API's ``Idempotency-Key`` header),
    error text NULL, created_at, updated_at

``findings``
    id UUID pk, job_id fk -> jobs ON DELETE CASCADE, scanner (ScannerName), rule_id,
    severity (Severity), file_path, line_start, line_end, message, status (FindingStatus),
    fingerprint text, created_at
    UNIQUE (job_id, fingerprint)   <- makes the scanner idempotent on redelivery

``patches``
    id UUID pk, finding_id fk -> findings, s3_key, model, verdict (Verdict) NULL,
    verification_key NULL, created_at

``processed_messages``  (consumer-side idempotency / inbox table)
    idempotency_key text pk, processed_at
"""

from __future__ import annotations

from patchloop_core.db.base import Base

__all__ = ["Base"]
