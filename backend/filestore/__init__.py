"""Local file storage for uploaded documents (files on disk, metadata in SQLite)."""

from .models import StoredFile
from .store import FileStore, FileStoreError, UnsupportedFileType

__all__ = ["FileStore", "FileStoreError", "StoredFile", "UnsupportedFileType"]
