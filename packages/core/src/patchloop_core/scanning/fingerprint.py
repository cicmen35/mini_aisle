from __future__ import annotations

from patchloop_core.scanning.base import RawFinding


def finding_fingerprint(finding: RawFinding, code_line: str) -> str:
    """Stable identity for a finding, used for dedupe (``UNIQUE (job_id, fingerprint)``).

    TODO(simon): return a hex sha256 over scanner, rule_id, file_path and the *normalized*
    offending code line (strip whitespace). Don't include line numbers: unrelated edits above
    the finding shift them, and the verifier needs to recognise "the same finding" after patching.
    """
    raise NotImplementedError("TODO(simon): finding_fingerprint")
