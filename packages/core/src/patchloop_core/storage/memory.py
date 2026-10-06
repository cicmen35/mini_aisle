from __future__ import annotations

from patchloop_core.storage.base import ArtifactNotFoundError


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        self.objects[key] = data

    def get_bytes(self, key: str) -> bytes:
        try:
            return self.objects[key]
        except KeyError:
            raise ArtifactNotFoundError(key) from None

    def exists(self, key: str) -> bool:
        return key in self.objects
