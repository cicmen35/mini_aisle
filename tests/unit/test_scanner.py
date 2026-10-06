"""Scanner layer: parsers and fingerprints (TODO(simon)), sources (mixed)."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from patchloop_core.domain import ScannerName, Severity
from patchloop_core.scanning import BanditRunner, ScannerError, ScannerRunner, run_tool
from patchloop_core.scanning.base import RawFinding
from patchloop_core.scanning.fingerprint import finding_fingerprint
from patchloop_core.scanning.parsers import parse_bandit, parse_pip_audit, parse_semgrep
from patchloop_scanner import sources
from patchloop_scanner.sources import clone_repo, make_tarball, safe_extract_tarball

# ---- plumbing ---------------------------------------------------------------------------


def test_runner_protocol() -> None:
    assert isinstance(BanditRunner(), ScannerRunner)


def test_run_tool_timeout_and_missing_binary(tmp_path: Path) -> None:
    with pytest.raises(ScannerError, match="timed out"):
        run_tool(["sleep", "5"], cwd=tmp_path, timeout_seconds=1)
    with pytest.raises(ScannerError, match="not installed"):
        run_tool(["definitely-not-a-tool"], cwd=tmp_path, timeout_seconds=1)


def test_run_tool_does_not_leak_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "leak-me")
    result = run_tool(["env"], cwd=tmp_path, timeout_seconds=5)
    assert b"leak-me" not in result.stdout


def test_make_tarball_skips_git_dir(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    (tmp_path / "app.py").write_text("print(1)")
    with tarfile.open(fileobj=io.BytesIO(make_tarball(tmp_path))) as tar:
        assert tar.getnames() == ["app.py"]


@pytest.mark.parametrize("url", ["file:///etc", "ssh://git@host/x", "ext::sh -c id", "http://x"])
def test_clone_rejects_non_https(url: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="https"):
        clone_repo(url, "HEAD", tmp_path / "dest")


# ---- TODO(simon): parsers ------------------------------------------------------------------


@pytest.mark.todo
def test_parse_bandit(fixtures_dir: Path) -> None:
    findings = parse_bandit((fixtures_dir / "scanner_outputs" / "bandit.json").read_bytes())
    by_rule = {f.rule_id: f for f in findings}
    assert {"B602", "B301", "B608"} <= set(by_rule)
    shell = by_rule["B602"]
    assert shell.scanner is ScannerName.BANDIT
    assert shell.file_path == "vulnapp/network.py"
    assert shell.line_start == 5
    assert shell.severity is Severity.HIGH
    assert shell.extra.get("cwe") == "78"


@pytest.mark.todo
def test_parse_semgrep(fixtures_dir: Path) -> None:
    findings = parse_semgrep((fixtures_dir / "scanner_outputs" / "semgrep.json").read_bytes())
    rules = {f.rule_id for f in findings}
    assert rules == {
        "patchloop.python.sql-injection-string-format",
        "patchloop.python.command-injection-shell-true",
        "patchloop.python.unsafe-deserialization",
        "patchloop.python.path-traversal-join",
    }
    traversal = next(f for f in findings if f.rule_id.endswith("path-traversal-join"))
    assert (traversal.file_path, traversal.line_start, traversal.severity) == (
        "vulnapp/reports.py",
        8,
        Severity.MEDIUM,
    )


@pytest.mark.todo
def test_parse_pip_audit(fixtures_dir: Path) -> None:
    findings = parse_pip_audit((fixtures_dir / "scanner_outputs" / "pip-audit.json").read_bytes())
    assert len(findings) == 12
    assert all(f.file_path == "requirements.txt" for f in findings)
    assert any("pyyaml" in f.message.lower() for f in findings)


@pytest.mark.todo
def test_parsers_tolerate_empty_results() -> None:
    assert parse_bandit(b'{"results": [], "errors": []}') == []
    assert parse_semgrep(b'{"results": [], "errors": []}') == []
    assert parse_pip_audit(b'{"dependencies": []}') == []


# ---- TODO(simon): fingerprint --------------------------------------------------------------

_F = RawFinding(ScannerName.BANDIT, "B602", Severity.HIGH, "vulnapp/network.py", 5, 5, "shell")


@pytest.mark.todo
def test_fingerprint_ignores_line_numbers_and_whitespace() -> None:
    moved = RawFinding(
        ScannerName.BANDIT, "B602", Severity.HIGH, "vulnapp/network.py", 42, 42, "shell"
    )
    code = 'result = subprocess.run(f"ping {host}", shell=True)'
    assert finding_fingerprint(_F, code) == finding_fingerprint(moved, f"    {code}  ")
    assert len(finding_fingerprint(_F, code)) == 64


@pytest.mark.todo
def test_fingerprint_differs_by_rule_file_and_code() -> None:
    code = "x = 1"
    other_rule = RawFinding(ScannerName.BANDIT, "B603", Severity.HIGH, _F.file_path, 5, 5, "m")
    other_file = RawFinding(ScannerName.BANDIT, "B602", Severity.HIGH, "other.py", 5, 5, "m")
    fps = {
        finding_fingerprint(_F, code),
        finding_fingerprint(other_rule, code),
        finding_fingerprint(other_file, code),
        finding_fingerprint(_F, "y = 2"),
    }
    assert len(fps) == 4


# ---- TODO(simon): safe extraction ----------------------------------------------------------


def _tar(members: list[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for info, data in members:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)
    return buf.getvalue()


def _file(name: str, data: bytes = b"x") -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


@pytest.mark.todo
def test_safe_extract_happy_path(tmp_path: Path, demo_app_dir: Path) -> None:
    safe_extract_tarball(make_tarball(demo_app_dir), tmp_path)
    assert (tmp_path / "vulnapp" / "users.py").is_file()


@pytest.mark.todo
@pytest.mark.parametrize("name", ["../evil.py", "/etc/evil", "a/../../evil.py"])
def test_safe_extract_rejects_traversal(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        safe_extract_tarball(_tar([_file(name)]), tmp_path / "out")
    assert not (tmp_path / "evil.py").exists()


@pytest.mark.todo
def test_safe_extract_rejects_symlink_escape(tmp_path: Path) -> None:
    link = tarfile.TarInfo("link")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    with pytest.raises(ValueError):
        safe_extract_tarball(_tar([(link, None)]), tmp_path / "out")


@pytest.mark.todo
def test_safe_extract_rejects_bombs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "MAX_MEMBERS", 3)
    with pytest.raises(ValueError):
        safe_extract_tarball(_tar([_file(f"f{i}") for i in range(5)]), tmp_path / "out")
