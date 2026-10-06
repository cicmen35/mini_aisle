"""Convert each tool's JSON output into ``RawFinding`` objects.

Real outputs captured from ``demo-targets/vulnerable-app`` live in
``tests/fixtures/scanner_outputs/``; the unit tests in ``tests/unit/test_scanner_parsers.py``
define what "correct" means.
"""

from __future__ import annotations

from patchloop_core.scanning.base import RawFinding


def parse_bandit(output: bytes) -> list[RawFinding]:
    """TODO(simon): parse ``bandit -f json`` output.

    Use ``results[*]``: ``test_id`` -> rule_id, ``issue_severity`` -> Severity (lowercase),
    ``filename`` (make it relative, strip a leading "./"), ``line_number`` / ``line_range``,
    ``issue_text`` -> message. Put ``issue_cwe.id`` into ``extra["cwe"]`` when present.
    """
    raise NotImplementedError("TODO(simon): parse_bandit")


def parse_semgrep(output: bytes) -> list[RawFinding]:
    """TODO(simon): parse ``semgrep --json`` output.

    Use ``results[*]``: ``check_id`` -> rule_id, ``extra.severity`` (ERROR/WARNING/INFO ->
    high/medium/low), ``path``, ``start.line`` / ``end.line``, ``extra.message``.
    Semgrep prefixes ``check_id`` with the rules directory (``opt.patchloop.rules...``); keep
    only the part starting at ``patchloop.`` so rule ids are stable across machines.
    """
    raise NotImplementedError("TODO(simon): parse_semgrep")


def parse_pip_audit(
    output: bytes, *, requirements_file: str = "requirements.txt"
) -> list[RawFinding]:
    """TODO(simon): parse ``pip-audit -f json`` output.

    One finding per (dependency, vulnerability): rule_id = vuln ``id`` (e.g. PYSEC-.../GHSA-...),
    severity = HIGH (pip-audit doesn't report severity), file_path = ``requirements_file``,
    line 1, message mentioning the package, version and ``fix_versions``.
    """
    raise NotImplementedError("TODO(simon): parse_pip_audit")
