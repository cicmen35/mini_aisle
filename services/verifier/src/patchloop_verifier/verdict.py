from __future__ import annotations

from patchloop_core.domain import Verdict


def decide_verdict(
    *,
    patch_applied: bool,
    target_fingerprint: str,
    fingerprints_before: frozenset[str],
    fingerprints_after: frozenset[str],
    tests_passed: bool | None,
) -> Verdict:
    """TODO(simon): pure decision function - the heart of "verify".

    - patch didn't apply -> PATCH_DOES_NOT_APPLY
    - ``target_fingerprint`` still in ``fingerprints_after`` -> STILL_VULNERABLE
    - any fingerprint in ``after`` that wasn't in ``before`` -> REGRESSION
    - ``tests_passed is False`` -> REGRESSION (``None`` means "no tests", which is allowed)
    - otherwise VERIFIED
    """
    raise NotImplementedError("TODO(simon): decide_verdict")
