"""Local file storage for uploaded documents (files on disk, metadata in SQLite)."""

from .models import StoredFile
from .permissions import Actor, PermissionDenied, Role, can_delete, can_edit, can_view
from .store import FileStore, FileStoreError, UnsupportedFileType

__all__ = [
    "Actor",
    "FileStore",
    "FileStoreError",
    "PermissionDenied",
    "Role",
    "StoredFile",
    "UnsupportedFileType",
    "can_delete",
    "can_edit",
    "can_view",
]
