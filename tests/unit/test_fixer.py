from __future__ import annotations

import pytest

from patchloop_fixer.patch import InvalidPatchError, extract_unified_diff, validate_patch_paths
from patchloop_fixer.prompt import FindingContext, build_fix_prompt

CTX = FindingContext(
    finding_id="f-1",
    rule_id="B602",
    message="subprocess call with shell=True identified",
    file_path="vulnapp/network.py",
    line_start=5,
    line_end=5,
    file_content='import subprocess\n\n\ndef ping(host):\n    return subprocess.run(f"ping -c 1 {host}", shell=True)\n',
)

DIFF = """--- a/vulnapp/network.py
+++ b/vulnapp/network.py
@@ -4,2 +4,2 @@
 def ping(host):
-    return subprocess.run(f"ping -c 1 {host}", shell=True)
+    return subprocess.run(["ping", "-c", "1", host])
"""


@pytest.mark.todo
def test_prompt_contains_context_and_is_deterministic() -> None:
    req = build_fix_prompt(CTX)
    assert req.temperature == 0
    assert req.messages[0].role == "system"
    assert "diff" in req.messages[0].content.lower()
    user = req.messages[-1].content
    for needle in ("B602", "vulnapp/network.py", "shell=True"):
        assert needle in user
    assert req.metadata["rule_id"] == "B602"
    assert build_fix_prompt(CTX) == req


@pytest.mark.todo
@pytest.mark.parametrize(
    "answer",
    [
        f"Here is the fix:\n```diff\n{DIFF}```\nThis removes shell=True.",
        f"```patch\n{DIFF}```",
        DIFF,
    ],
)
def test_extract_unified_diff(answer: str) -> None:
    assert extract_unified_diff(answer) == DIFF


@pytest.mark.todo
@pytest.mark.parametrize("answer", ["I cannot help with that.", "```python\nprint(1)\n```", ""])
def test_extract_rejects_non_diffs(answer: str) -> None:
    with pytest.raises(InvalidPatchError):
        extract_unified_diff(answer)


@pytest.mark.todo
def test_validate_accepts_target_file() -> None:
    validate_patch_paths(DIFF, allowed_file="vulnapp/network.py")


@pytest.mark.todo
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("a/vulnapp/users.py", "b/vulnapp/users.py"),
        ("a/../../etc/passwd", "b/../../etc/passwd"),
        ("/etc/passwd", "/etc/passwd"),
        ("/dev/null", "b/vulnapp/network.py"),
    ],
)
def test_validate_rejects_other_paths(old: str, new: str) -> None:
    evil = DIFF.replace("a/vulnapp/network.py", old, 1).replace("b/vulnapp/network.py", new, 1)
    with pytest.raises(InvalidPatchError):
        validate_patch_paths(evil, allowed_file="vulnapp/network.py")
