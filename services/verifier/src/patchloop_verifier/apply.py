from __future__ import annotations

from pathlib import Path


def apply_patch(workdir: Path, diff: str, *, timeout_seconds: int = 30) -> bool:
    """TODO(simon): apply ``diff`` inside ``workdir``. Return ``False`` if it doesn't apply.

    Use ``run_tool(["git", "apply", "--check", ...])`` first, then ``git apply`` (both with
    ``--unsafe-paths`` *off*, which is the default - know why). ``workdir`` doesn't need to be a
    git repo. Feed the diff via a temp file, not a shell. Tests: tests/unit/test_verifier.py.
    """
    raise NotImplementedError("TODO(simon): apply_patch")
