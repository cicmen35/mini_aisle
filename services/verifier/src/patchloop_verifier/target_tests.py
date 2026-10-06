"""Run the target project's own test-suite after patching."""

from __future__ import annotations

import sys
from pathlib import Path

from patchloop_core.scanning.base import ScannerError, run_tool


def run_target_tests(workdir: Path, *, timeout_seconds: int = 180) -> bool | None:
    """``True``/``False`` for pass/fail, ``None`` if the target has no ``tests/`` directory.

    Runs with the verifier's sandboxed tool environment (no network in kind via NetworkPolicy).
    """
    if not (workdir / "tests").is_dir():
        return None
    try:
        run_tool(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            cwd=workdir,
            timeout_seconds=timeout_seconds,
            extra_env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(workdir)},
        )
    except ScannerError:
        return False
    return True
