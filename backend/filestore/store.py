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
from .permissions import Actor, PermissionDenied, can_delete, can_edit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    extension         TEXT NOT NULL,
    category          TEXT NOT NULL DEFAULT '',
    uploader_id       TEXT NOT NULL CHECK (length(trim(uploader_id)) > 0),
    uploaded_at       TEXT NOT NULL,
    size              INTEGER NOT NULL,
    is_private        INTEGER NOT NULL DEFAULT 0 CHECK (is_private IN (0, 1)),
    index_id          TEXT
);
CREATE TRIGGER IF NOT EXISTS files_uploader_id_immutable
BEFORE UPDATE OF uploader_id ON files
WHEN NEW.uploader_id IS NOT OLD.uploader_id
BEGIN
    SELECT RAISE(ABORT, 'uploader_id is immutable');
END;
CREATE TABLE IF NOT EXISTS file_labels (
    file_id  TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    label    TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (file_id, label)
);
CREATE INDEX IF NOT EXISTS idx_file_labels_label ON file_labels(label);
CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
CREATE INDEX IF NOT EXISTS idx_files_uploader_id ON files(uploader_id);
CREATE INDEX IF NOT EXISTS idx_files_index_id ON files(index_id);
"""

_COLUMNS = (
    "id, name, original_filename, extension, category, uploader_id, uploaded_at, size,"
    " is_private, index_id"
)


def _visibility_clause(viewer: Actor | None) -> tuple[str | None, list[str]]:
    """SQL condition limiting rows to what *viewer* may see (``None`` = no limit)."""
    if viewer is None or viewer.is_admin:
        return None, []
    return "(is_private = 0 OR uploader_id = ?)", [viewer.user_id]


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

    Read methods take an optional ``viewer``: when given, private files of
    other users are hidden (admins see everything). ``viewer=None`` means
    trusted internal access with no filtering -- request handlers must always
    pass the authenticated :class:`Actor`. Editing and deleting always require
    an ``actor`` and are admin-only (see :mod:`filestore.permissions`).
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
            uploader_id=str(row["uploader_id"]),
            uploaded_at=datetime.fromisoformat(str(row["uploaded_at"])),
            labels=tuple(labels),
            size=int(row["size"]),
            path=self._blob_path(file_id, extension),
            is_private=bool(row["is_private"]),
            index_id=None if row["index_id"] is None else str(row["index_id"]),
        )

    def _get_where(
        self, column: str, value: str, viewer: Actor | None
    ) -> StoredFile | None:
        clauses = [f"{column} = ?"]
        params = [value]
        vis, vis_params = _visibility_clause(viewer)
        if vis:
            clauses.append(vis)
            params += vis_params
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM files WHERE {' AND '.join(clauses)}", params
            ).fetchone()
            if row is None:
                return None
            file_id = str(row["id"])
            labels = self._labels_for(conn, [file_id])[file_id]
        return self._to_model(row, labels)

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
        uploader_id: str,
        filename: str | None = None,
        name: str | None = None,
        category: str = "",
        labels: Iterable[str] = (),
        is_private: bool = False,
    ) -> StoredFile:
        """Store a file and its metadata; returns the new :class:`StoredFile`.

        *source* is either a filesystem path or a readable binary stream (e.g.
        FastAPI's ``UploadFile.file``). For streams, *filename* is required so
        the extension can be validated. *uploader_id* is the authenticated
        user's id and cannot be changed afterwards. Files are public unless
        *is_private* is set.
        """
        uploader_id = uploader_id.strip()
        if not uploader_id:
            raise ValueError("uploader_id is required")

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
                    f"INSERT INTO files ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        file_id,
                        (name or "").strip() or filename,
                        filename,
                        extension,
                        category.strip(),
                        uploader_id,
                        uploaded_at.isoformat(),
                        size,
                        int(is_private),
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
        actor: Actor,
        name: str | None = None,
        category: str | None = None,
        labels: Iterable[str] | None = None,
        is_private: bool | None = None,
    ) -> StoredFile:
        """Edit a file's metadata on behalf of *actor*. ``None`` leaves a field unchanged.

        Raises :class:`FileStoreError` if the file does not exist or *actor*
        cannot see it, and :class:`PermissionDenied` if *actor* may not edit it.
        The uploader can never be changed. When *is_private* changes, the
        caller must mirror it into the search index as well.
        """
        current = self.get(file_id, viewer=actor)
        if current is None:
            raise FileStoreError(f"no file with id '{file_id}'")
        if not can_edit(actor, current):
            raise PermissionDenied(f"'{actor.user_id}' may not edit file '{file_id}'")

        with self._connect() as conn:
            if name is not None and name.strip():
                conn.execute("UPDATE files SET name = ? WHERE id = ?", (name.strip(), file_id))
            if category is not None:
                conn.execute(
                    "UPDATE files SET category = ? WHERE id = ?", (category.strip(), file_id)
                )
            if labels is not None:
                self._write_labels(conn, file_id, normalize_labels(labels))
            if is_private is not None:
                conn.execute(
                    "UPDATE files SET is_private = ? WHERE id = ?", (int(is_private), file_id)
                )

        stored = self.get(file_id)
        assert stored is not None
        return stored

    def set_index_id(self, file_id: str, index_id: str) -> None:
        """Link a file to its search-index entry (system bookkeeping after indexing)."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE files SET index_id = ? WHERE id = ?", (index_id, file_id)
            )
            if cur.rowcount == 0:
                raise FileStoreError(f"no file with id '{file_id}'")

    def clear_index_id(self, file_id: str) -> None:
        """Unlink a file from the search index (e.g. after it was re-indexed away)."""
        with self._connect() as conn:
            conn.execute("UPDATE files SET index_id = NULL WHERE id = ?", (file_id,))

    def delete(self, file_id: str, *, actor: Actor) -> bool:
        """Remove the metadata row (labels cascade) and the blob on behalf of *actor*.

        Returns ``False`` if the file does not exist or *actor* cannot see it;
        raises :class:`PermissionDenied` if *actor* may not delete it.
        """
        current = self.get(file_id, viewer=actor)
        if current is None:
            return False
        if not can_delete(actor, current):
            raise PermissionDenied(f"'{actor.user_id}' may not delete file '{file_id}'")
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            if cur.rowcount == 0:
                return False
        current.path.unlink(missing_ok=True)
        return True

    # -- read ------------------------------------------------------------
    def get(self, file_id: str, *, viewer: Actor | None = None) -> StoredFile | None:
        """The file with *file_id*, or ``None`` if missing or hidden from *viewer*."""
        return self._get_where("id", file_id, viewer)

    def get_by_index_id(
        self, index_id: str, *, viewer: Actor | None = None
    ) -> StoredFile | None:
        """Look up a file from a search hit's document id."""
        return self._get_where("index_id", index_id, viewer)

    def list_files(
        self,
        *,
        viewer: Actor | None = None,
        category: str | None = None,
        uploader_id: str | None = None,
        label: str | None = None,
        is_private: bool | None = None,
    ) -> list[StoredFile]:
        """Stored files visible to *viewer*, newest first, optionally filtered."""
        clauses: list[str] = []
        params: list[str | int] = []
        vis, vis_params = _visibility_clause(viewer)
        if vis:
            clauses.append(vis)
            params += vis_params
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if uploader_id is not None:
            clauses.append("uploader_id = ?")
            params.append(uploader_id)
        if label is not None:
            clauses.append("id IN (SELECT file_id FROM file_labels WHERE label = ?)")
            params.append(label)
        if is_private is not None:
            clauses.append("is_private = ?")
            params.append(int(is_private))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM files{where} ORDER BY uploaded_at DESC, rowid DESC",
                params,
            ).fetchall()
            labels = self._labels_for(conn, [str(r["id"]) for r in rows])
        return [self._to_model(r, labels[str(r["id"])]) for r in rows]
