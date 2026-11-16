from __future__ import annotations

import os
import shutil
import sqlite3
import uuid
from collections.abc import Generator, Iterable, Sequence
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from .config import ALLOWED_EXTENSIONS, DB_NAME, STORAGE_DIR
from .models import StoredFile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    extension         TEXT NOT NULL,
    category          TEXT NOT NULL DEFAULT '',
    uploader          TEXT NOT NULL DEFAULT '',
    uploaded_at       TEXT NOT NULL,
    size              INTEGER NOT NULL,
    index_id          TEXT
);
CREATE TABLE IF NOT EXISTS file_labels (
    file_id  TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    label    TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (file_id, label)
);
CREATE INDEX IF NOT EXISTS idx_file_labels_label ON file_labels(label);
CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
CREATE INDEX IF NOT EXISTS idx_files_uploader ON files(uploader);
CREATE INDEX IF NOT EXISTS idx_files_index_id ON files(index_id);
"""

_COLUMNS = (
    "id, name, original_filename, extension, category, uploader, uploaded_at, size, index_id"
)


class FileStoreError(LookupError):
    """Raised when a requested file does not exist in the store."""


class UnsupportedFileType(ValueError):
    """Raised when a file's extension is not in ``ALLOWED_EXTENSIONS``."""


def normalize_labels(labels: Iterable[str]) -> tuple[str, ...]:
    """Strip whitespace, drop empties and duplicates, keep first-seen order."""
    seen: dict[str, None] = {}
    for raw in labels:
        label = raw.strip()
        if label:
            seen.setdefault(label, None)
    return tuple(seen)


class FileStore:
    """Stores uploaded documents on the local disk with metadata in SQLite.

    Blobs live at ``<root>/<id><ext>``; metadata (name, category, uploader,
    upload date, labels, ...) lives in a single SQLite file.
    """

    def __init__(
        self,
        root: Path | str = STORAGE_DIR,
        db_path: Path | str | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path is not None else self.root / DB_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # -- internals -------------------------------------------------------
    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Short-lived connection; commits on success, rolls back on error."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn

    def _blob_path(self, file_id: str, extension: str) -> Path:
        return self.root / f"{file_id}{extension}"

    def _labels_for(
        self, conn: sqlite3.Connection, ids: Sequence[str]
    ) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {i: [] for i in ids}
        if not ids:
            return out
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT file_id, label FROM file_labels WHERE file_id IN ({placeholders})"
            " ORDER BY file_id, position",
            list(ids),
        ).fetchall()
        for row in rows:
            out[str(row["file_id"])].append(str(row["label"]))
        return out

    def _to_model(self, row: sqlite3.Row, labels: Sequence[str]) -> StoredFile:
        file_id = str(row["id"])
        extension = str(row["extension"])
        return StoredFile(
            id=file_id,
            name=str(row["name"]),
            original_filename=str(row["original_filename"]),
            extension=extension,
            category=str(row["category"]),
            uploader=str(row["uploader"]),
            uploaded_at=datetime.fromisoformat(str(row["uploaded_at"])),
            labels=tuple(labels),
            size=int(row["size"]),
            path=self._blob_path(file_id, extension),
            index_id=None if row["index_id"] is None else str(row["index_id"]),
        )

    @staticmethod
    def _write_labels(
        conn: sqlite3.Connection, file_id: str, labels: Sequence[str]
    ) -> None:
        conn.execute("DELETE FROM file_labels WHERE file_id = ?", (file_id,))
        conn.executemany(
            "INSERT INTO file_labels (file_id, label, position) VALUES (?, ?, ?)",
            [(file_id, label, pos) for pos, label in enumerate(labels)],
        )

    # -- write -----------------------------------------------------------
    def save(
        self,
        source: Path | str | BinaryIO,
        *,
        filename: str | None = None,
        uploader: str = "",
        name: str | None = None,
        category: str = "",
        labels: Iterable[str] = (),
    ) -> StoredFile:
        """Store a file and its metadata; returns the new :class:`StoredFile`.

        *source* is either a filesystem path or a readable binary stream (e.g.
        FastAPI's ``UploadFile.file``). For streams, *filename* is required so
        the extension can be validated.
        """
        if isinstance(source, (str, Path)):
            src_path: Path | None = Path(source)
            filename = filename or src_path.name
        else:
            src_path = None
            if not filename:
                raise ValueError("filename is required when saving from a stream")

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileType(
                f"'{filename}' has an unsupported extension; "
                f"expected one of {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file_id = uuid.uuid4().hex
        dest = self._blob_path(file_id, extension)
        tmp = dest.with_name(dest.name + ".part")
        try:
            if src_path is not None:
                shutil.copyfile(src_path, tmp)
            else:
                assert not isinstance(source, (str, Path))
                with tmp.open("wb") as out:
                    shutil.copyfileobj(source, out)
            os.replace(tmp, dest)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

        clean_labels = normalize_labels(labels)
        uploaded_at = datetime.now(timezone.utc)
        size = dest.stat().st_size
        try:
            with self._connect() as conn:
                conn.execute(
                    f"INSERT INTO files ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        file_id,
                        (name or "").strip() or filename,
                        filename,
                        extension,
                        category.strip(),
                        uploader.strip(),
                        uploaded_at.isoformat(),
                        size,
                    ),
                )
                self._write_labels(conn, file_id, clean_labels)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise

        stored = self.get(file_id)
        assert stored is not None
        return stored

    def update(
        self,
        file_id: str,
        *,
        name: str | None = None,
        category: str | None = None,
        labels: Iterable[str] | None = None,
        index_id: str | None = None,
    ) -> StoredFile:
        """Edit a file's metadata. ``None`` leaves a field unchanged.

        Use :meth:`clear_index_id` to remove the search-index link.
        """
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM files WHERE id = ?", (file_id,)).fetchone()
            if exists is None:
                raise FileStoreError(f"no file with id '{file_id}'")
            if name is not None and name.strip():
                conn.execute("UPDATE files SET name = ? WHERE id = ?", (name.strip(), file_id))
            if category is not None:
                conn.execute(
                    "UPDATE files SET category = ? WHERE id = ?", (category.strip(), file_id)
                )
            if labels is not None:
                self._write_labels(conn, file_id, normalize_labels(labels))
            if index_id is not None:
                conn.execute(
                    "UPDATE files SET index_id = ? WHERE id = ?", (index_id, file_id)
                )

        stored = self.get(file_id)
        assert stored is not None
        return stored

    def clear_index_id(self, file_id: str) -> None:
        """Unlink a file from the search index (e.g. after it was re-indexed away)."""
        with self._connect() as conn:
            conn.execute("UPDATE files SET index_id = NULL WHERE id = ?", (file_id,))

    def delete(self, file_id: str) -> bool:
        """Remove the metadata row (labels cascade) and the blob.

        Returns ``True`` if the file was known to the store.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT extension FROM files WHERE id = ?", (file_id,)
            ).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self._blob_path(file_id, str(row["extension"])).unlink(missing_ok=True)
        return True

    # -- read ------------------------------------------------------------
    def get(self, file_id: str) -> StoredFile | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM files WHERE id = ?", (file_id,)
            ).fetchone()
            if row is None:
                return None
            labels = self._labels_for(conn, [file_id])[file_id]
        return self._to_model(row, labels)

    def get_by_index_id(self, index_id: str) -> StoredFile | None:
        """Look up a file from a search hit's document id."""
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM files WHERE index_id = ?", (index_id,)
            ).fetchone()
            if row is None:
                return None
            file_id = str(row["id"])
            labels = self._labels_for(conn, [file_id])[file_id]
        return self._to_model(row, labels)

    def list_files(
        self,
        *,
        category: str | None = None,
        uploader: str | None = None,
        label: str | None = None,
    ) -> list[StoredFile]:
        """All stored files, newest first, optionally filtered."""
        clauses: list[str] = []
        params: list[str] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if uploader is not None:
            clauses.append("uploader = ?")
            params.append(uploader)
        if label is not None:
            clauses.append("id IN (SELECT file_id FROM file_labels WHERE label = ?)")
            params.append(label)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM files{where} ORDER BY uploaded_at DESC, rowid DESC",
                params,
            ).fetchall()
            labels = self._labels_for(conn, [str(r["id"]) for r in rows])
        return [self._to_model(r, labels[str(r["id"])]) for r in rows]
