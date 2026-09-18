"""对象存储抽象：默认本地 data/，可通过 BLOB_STORE 切换实现。"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class BlobStore(Protocol):
    def put_bytes(self, content: bytes, filename: str, *, category: str = "uploads") -> str:
        """Persist bytes and return a stored reference (path or URI)."""

    def resolve_path(self, stored_ref: str) -> Path:
        """Resolve a stored reference to a local readable path."""

    def delete(self, stored_ref: str) -> None:
        """Delete a stored object if it exists."""


class LocalBlobStore:
    def _category_dir(self, category: str) -> Path:
        mapping = {
            "uploads": settings.uploads_dir,
            "extracted": settings.extracted_dir,
            "reports": settings.reports_dir,
        }
        directory = mapping.get(category, settings.uploads_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def put_bytes(self, content: bytes, filename: str, *, category: str = "uploads") -> str:
        suffix = Path(filename).suffix.lower()
        directory = self._category_dir(category)
        stored_path = directory / f"{uuid.uuid4().hex}{suffix}"
        stored_path.write_bytes(content)
        return str(stored_path)

    def resolve_path(self, stored_ref: str) -> Path:
        return Path(stored_ref)

    def delete(self, stored_ref: str) -> None:
        path = Path(stored_ref)
        if path.is_file():
            path.unlink(missing_ok=True)


_blob_store: BlobStore | None = None


def get_blob_store() -> BlobStore:
    global _blob_store
    if _blob_store is not None:
        return _blob_store
    backend = os.getenv("BLOB_STORE", "local").strip().lower()
    if backend == "local":
        _blob_store = LocalBlobStore()
        return _blob_store
    raise RuntimeError(f"Unsupported BLOB_STORE backend: {backend}")


def reset_blob_store_for_tests() -> None:
    global _blob_store
    _blob_store = None
