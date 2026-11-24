from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StoredFile:
    """Metadata of one file kept in the :class:`~filestore.FileStore`."""

    id: str
    name: str
    original_filename: str
    extension: str
    category: str
    uploader_id: str  # id of the authenticated user who uploaded the file; never changes
    uploaded_at: datetime
    labels: tuple[str, ...]
    size: int
    path: Path
    is_private: bool = False  # private files are visible only to the uploader and admins
    index_id: str | None = None  # id of the file's entry in the search index, if any

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly representation (ISO date, list labels, str path)."""
        return {
            "id": self.id,
            "name": self.name,
            "original_filename": self.original_filename,
            "extension": self.extension,
            "category": self.category,
            "uploader_id": self.uploader_id,
            "uploaded_at": self.uploaded_at.isoformat(),
            "labels": list(self.labels),
            "size": self.size,
            "path": str(self.path),
            "is_private": self.is_private,
            "index_id": self.index_id,
        }
