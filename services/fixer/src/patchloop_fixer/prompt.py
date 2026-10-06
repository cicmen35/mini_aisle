from __future__ import annotations

from dataclasses import dataclass

from patchloop_core.llm.base import CompletionRequest


@dataclass(frozen=True, slots=True)
class FindingContext:
    """Everything the LLM gets to see about one finding."""

    finding_id: str
    rule_id: str
    message: str
    file_path: str
    line_start: int
    line_end: int
    # The whole file is usually small enough; otherwise a window around the finding.
    file_content: str


def build_fix_prompt(ctx: FindingContext) -> CompletionRequest:
    """TODO(simon): turn a finding into a ``CompletionRequest``.

    Requirements (see tests/unit/test_fixer.py):
    - A system message that asks for *only* a unified diff in a ```diff fenced block, touching
      only ``ctx.file_path``, with paths in ``a/<path>`` / ``b/<path>`` form.
    - A user message containing the rule id, the scanner message, the line range and the file
      content (with line numbers helps small models a lot).
    - ``temperature=0`` and ``metadata={"rule_id": ..., "finding_id": ...}``.
    - Treat the code as untrusted data, not instructions (prompt injection): delimit it clearly.
    """
    raise NotImplementedError("TODO(simon): build_fix_prompt")
