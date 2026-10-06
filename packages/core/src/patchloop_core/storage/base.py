"""Artifact store contract (S3 in compose/kind, in-memory in unit tests).

Keys come from ``patchloop_core.messages.S3Keys``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ArtifactNotFoundError(KeyError):
    pass


@runtime_checkable
class ArtifactStore(Protocol):
    def put_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None: ...

    def get_bytes(self, key: str) -> bytes:
        """Raises ``ArtifactNotFoundError`` if the key doesn't exist."""
        ...

    def exists(self, key: str) -> bool: ...
