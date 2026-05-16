"""Stub for object/blob storage (receipts, document scans, voice memos).

Phase 4+ will implement Hetzner Object Storage / local-disk backends behind
:class:`Storage`. Kept here so signatures can stabilize across phases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    """Minimal blob-storage surface."""

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        """Store ``data`` under ``key``; return a stable retrieval URL/identifier."""
        ...

    async def get(self, key: str) -> bytes:
        """Fetch the bytes for ``key``."""
        ...

    async def delete(self, key: str) -> None:
        """Delete the object at ``key`` (no-op if missing)."""
        ...


class LocalDiskStorage:
    """Trivial local-disk implementation for development / testing."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    async def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()
