from __future__ import annotations


class InvalidPatchError(ValueError):
    pass


def extract_unified_diff(llm_text: str) -> str:
    """TODO(simon): pull the unified diff out of an LLM answer.

    Accept a ```diff (or ```patch, or bare ```) fenced block, or a raw diff starting with
    ``--- ``. Return it with a trailing newline. Raise ``InvalidPatchError`` if there is no
    ``---``/``+++``/``@@`` structure.
    """
    raise NotImplementedError("TODO(simon): extract_unified_diff")


def validate_patch_paths(diff: str, *, allowed_file: str) -> None:
    """TODO(simon): the LLM output is untrusted. Raise ``InvalidPatchError`` unless every
    ``---``/``+++`` header refers to ``allowed_file`` (with optional ``a/``/``b/`` prefix).
    Reject absolute paths, ``..`` segments, ``/dev/null`` (file creation/deletion) and
    anything that would touch a different file.
    """
    raise NotImplementedError("TODO(simon): validate_patch_paths")
