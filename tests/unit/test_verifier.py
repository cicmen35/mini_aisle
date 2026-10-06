from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from patchloop_core.domain import Verdict
from patchloop_verifier.apply import apply_patch
from patchloop_verifier.target_tests import run_target_tests
from patchloop_verifier.verdict import decide_verdict

SQLI_FIX = """--- a/vulnapp/users.py
+++ b/vulnapp/users.py
@@ -14,4 +14,4 @@
 def find_user(conn: sqlite3.Connection, name: str) -> list[tuple[int, str, str]]:
     cur = conn.cursor()
-    query = f"SELECT id, name, email FROM users WHERE name = '{name}'"
-    cur.execute(query)
+    query = "SELECT id, name, email FROM users WHERE name = ?"
+    cur.execute(query, (name,))
"""


@pytest.fixture
def workdir(tmp_path: Path, demo_app_dir: Path) -> Path:
    dest = tmp_path / "app"
    shutil.copytree(demo_app_dir, dest)
    return dest


# ---- plumbing ---------------------------------------------------------------------------


def test_demo_target_tests_pass_before_patching(workdir: Path) -> None:
    assert run_target_tests(workdir) is True


def test_no_tests_means_none(tmp_path: Path) -> None:
    assert run_target_tests(tmp_path) is None


def test_broken_target_tests_are_detected(workdir: Path) -> None:
    (workdir / "vulnapp" / "users.py").write_text("raise SystemExit(1)\n")
    assert run_target_tests(workdir) is False


# ---- TODO(simon) --------------------------------------------------------------------------


@pytest.mark.todo
def test_apply_good_patch_keeps_tests_green(workdir: Path) -> None:
    assert apply_patch(workdir, SQLI_FIX) is True
    assert "WHERE name = ?" in (workdir / "vulnapp" / "users.py").read_text()
    assert run_target_tests(workdir) is True


@pytest.mark.todo
def test_apply_rejects_patch_that_does_not_apply(workdir: Path) -> None:
    stale = SQLI_FIX.replace("cur = conn.cursor()", "cur = conn.cursor(42)")
    before = (workdir / "vulnapp" / "users.py").read_text()
    assert apply_patch(workdir, stale) is False
    assert (workdir / "vulnapp" / "users.py").read_text() == before


@pytest.mark.todo
def test_apply_refuses_paths_outside_workdir(workdir: Path) -> None:
    evil = SQLI_FIX.replace("a/vulnapp/users.py", "a/../outside.py").replace(
        "b/vulnapp/users.py", "b/../outside.py"
    )
    assert apply_patch(workdir, evil) is False
    assert not (workdir.parent / "outside.py").exists()


@pytest.mark.todo
@pytest.mark.parametrize(
    ("applied", "after", "tests", "expected"),
    [
        (False, set(), True, Verdict.PATCH_DOES_NOT_APPLY),
        (True, {"target"}, True, Verdict.STILL_VULNERABLE),
        (True, {"other", "new"}, True, Verdict.REGRESSION),
        (True, {"other"}, False, Verdict.REGRESSION),
        (True, {"other"}, None, Verdict.VERIFIED),
        (True, set(), True, Verdict.VERIFIED),
    ],
)
def test_decide_verdict(
    applied: bool, after: set[str], tests: bool | None, expected: Verdict
) -> None:
    assert (
        decide_verdict(
            patch_applied=applied,
            target_fingerprint="target",
            fingerprints_before=frozenset({"target", "other"}),
            fingerprints_after=frozenset(after),
            tests_passed=tests,
        )
        is expected
    )
