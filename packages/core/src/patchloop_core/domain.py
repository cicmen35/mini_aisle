"""Domain vocabulary shared by the API, the workers and the DB layer."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle of a scan job.

    queued -> scanning -> fixing -> verifying -> completed
    any non-terminal state -> failed
    """

    QUEUED = "queued"
    SCANNING = "scanning"
    FIXING = "fixing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {JobStatus.COMPLETED, JobStatus.FAILED}


class FindingStatus(StrEnum):
    """Lifecycle of one finding: open -> fix_proposed -> verified | rejected | fix_failed."""

    OPEN = "open"
    FIX_PROPOSED = "fix_proposed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    FIX_FAILED = "fix_failed"

    @property
    def is_terminal(self) -> bool:
        return self in {FindingStatus.VERIFIED, FindingStatus.REJECTED, FindingStatus.FIX_FAILED}


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScannerName(StrEnum):
    SEMGREP = "semgrep"
    BANDIT = "bandit"
    PIP_AUDIT = "pip-audit"


class Verdict(StrEnum):
    """Outcome of verifying one patch."""

    VERIFIED = "verified"  # patch applies, finding gone, no new findings, tests pass
    STILL_VULNERABLE = "still_vulnerable"  # the original finding is still reported
    REGRESSION = "regression"  # new findings introduced, or tests broke
    PATCH_DOES_NOT_APPLY = "patch_does_not_apply"
