"""Scanner-runner contract. Shared by the scanner (find) and the verifier (re-scan after patching)."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from patchloop_core.domain import ScannerName, Severity

MAX_OUTPUT_BYTES = 10 * 1024 * 1024
TMP_DIR = tempfile.gettempdir()


@dataclass(frozen=True, slots=True)
class RawFinding:
    """A tool-agnostic finding. ``file_path`` is relative to the scanned directory."""

    scanner: ScannerName
    rule_id: str
    severity: Severity
    file_path: str
    line_start: int
    line_end: int
    message: str
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScanReport:
    scanner: ScannerName
    findings: tuple[RawFinding, ...]
    raw_output: bytes  # stored to S3 for auditing
    exit_code: int
    duration_seconds: float


class ScannerError(RuntimeError):
    pass


@runtime_checkable
class ScannerRunner(Protocol):
    name: ScannerName

    def run(self, target_dir: Path) -> ScanReport: ...


@dataclass(frozen=True, slots=True)
class ToolResult:
    argv: tuple[str, ...]
    exit_code: int
    stdout: bytes
    stderr: bytes
    duration_seconds: float


def run_tool(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    ok_exit_codes: frozenset[int] = frozenset({0}),
    extra_env: dict[str, str] | None = None,
) -> ToolResult:
    """Run an external tool on untrusted code.

    No shell (argv list only), a minimal environment (no credentials leak into the tool),
    a hard timeout, and capped output. Process-level isolation (non-root, read-only rootfs,
    no capabilities, pids/memory limits) is enforced by the container, see docker-compose.yml.
    """
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": TMP_DIR, "LANG": "C.UTF-8"}
    env.update(extra_env or {})
    started = time.monotonic()
    try:
        # argv list and no shell, so no shell injection is possible.
        proc = subprocess.run(  # noqa: S603  # nosec B603
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScannerError(f"{argv[0]} timed out after {timeout_seconds}s") from exc
    except FileNotFoundError as exc:
        raise ScannerError(f"{argv[0]} is not installed") from exc
    if proc.returncode not in ok_exit_codes:
        raise ScannerError(
            f"{argv[0]} exited {proc.returncode}: {proc.stderr[-2000:].decode(errors='replace')}"
        )
    return ToolResult(
        argv=tuple(argv),
        exit_code=proc.returncode,
        stdout=proc.stdout[:MAX_OUTPUT_BYTES],
        stderr=proc.stderr[:MAX_OUTPUT_BYTES],
        duration_seconds=time.monotonic() - started,
    )
