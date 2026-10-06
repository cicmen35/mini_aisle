"""Getting untrusted source code onto local disk, and snapshotting it for the fixer/verifier."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from patchloop_core.scanning.base import run_tool

MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_MEMBERS = 20_000


def safe_extract_tarball(data: bytes, dest: Path) -> None:
    """Extract an *untrusted* ``.tar.gz`` into ``dest``.

    TODO(simon): implement without trusting the archive. Reject (raise ``ValueError``) when:
    - a member path is absolute or escapes ``dest`` after resolution ("../../etc/passwd"),
    - a member is a symlink/hardlink pointing outside ``dest``, or a device/fifo,
    - more than ``MAX_MEMBERS`` members or more than ``MAX_EXTRACTED_BYTES`` total (zip bomb).
    Python 3.12's ``tarfile`` ``filter="data"`` covers part of this - know what it does and
    doesn't do. Tests: tests/unit/test_scanner_sources.py.
    """
    raise NotImplementedError("TODO(simon): safe_extract_tarball")


def make_tarball(src_dir: Path) -> bytes:
    """Pack ``src_dir`` (without ``.git``) into a deterministic-ish ``.tar.gz``."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(src_dir.rglob("*")):
            rel = path.relative_to(src_dir)
            if rel.parts and rel.parts[0] == ".git":
                continue
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                continue
            tar.add(path, arcname=str(rel), recursive=False)
    return buf.getvalue()


def clone_repo(repo_url: str, ref: str, dest: Path, *, timeout_seconds: int = 120) -> None:
    """Shallow-clone a public repo over HTTPS. Hooks, credential prompts and local/ssh/ext
    protocols are disabled so a malicious URL can't read local files or run commands."""
    if not repo_url.startswith("https://"):
        raise ValueError("only https:// repositories are supported")
    git_safe = [
        "-c",
        "protocol.allow=never",
        "-c",
        "protocol.https.allow=always",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "credential.helper=",
    ]
    clone = ["git", *git_safe, "clone", "--quiet", "--depth", "1", "--no-tags"]
    if ref != "HEAD":
        clone += ["--branch", ref]
    run_tool(
        [*clone, "--", repo_url, str(dest)],
        cwd=dest.parent,
        timeout_seconds=timeout_seconds,
        extra_env={"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"},
    )
