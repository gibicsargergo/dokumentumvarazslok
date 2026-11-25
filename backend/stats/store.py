from __future__ import annotations

import sqlite3
from collections.abc import Generator, Iterable
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .config import DEFAULT_MONTHS, STATS_DB

Mode = Literal["search", "chat"]
Kind = Literal["document", "category"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    mode        TEXT NOT NULL CHECK (mode IN ('search', 'chat')),
    query       TEXT NOT NULL,
    answer      TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS query_hits (
    query_id  INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
    file_id   TEXT,
    title     TEXT NOT NULL DEFAULT '',
    category  TEXT NOT NULL DEFAULT '',
    rank      INTEGER NOT NULL,
    score     REAL NOT NULL,
    UNIQUE (query_id, file_id)
);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at);
CREATE INDEX IF NOT EXISTS idx_query_hits_file_id ON query_hits(file_id);
"""


@dataclass(frozen=True)
class QueryHit:
    """One document returned for a query.

    *file_id* is the FileStore id (``None`` if the indexed chunk is not linked
    to a stored file). *title* and *category* are snapshots taken at query
    time, so later edits or deletion do not rewrite history.
    """

    file_id: str | None
    title: str
    category: str
    rank: int
    score: float


def month_keys(count: int, now: datetime | None = None) -> list[str]:
    """The last *count* months as ``YYYY-MM``, oldest first, ending with *now*'s month."""
    now = now or datetime.now(timezone.utc)
    year, month = now.year, now.month
    keys: list[str] = []
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()
    return keys


class StatsStore:
    """Logs every question (and its answer) plus the documents it surfaced.

    A document counts at most once per query, even when several of its chunks
    matched; the same holds for a category.
    """

    def __init__(self, db_path: Path | str = STATS_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Short-lived connection; commits on success, rolls back on error."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn

    # -- write -----------------------------------------------------------
    def log_query(
        self,
        *,
        user_id: str,
        mode: Mode,
        query: str,
        hits: Iterable[QueryHit],
    ) -> int:
        """Record a query and the documents it returned; returns the query id."""
        # Keep only the best-ranked hit per file (unlinked hits are all kept).
        unique: list[QueryHit] = []
        seen: set[str] = set()
        for hit in sorted(hits, key=lambda h: h.rank):
            if hit.file_id is not None:
                if hit.file_id in seen:
                    continue
                seen.add(hit.file_id)
            unique.append(hit)

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO queries (user_id, mode, query, created_at) VALUES (?, ?, ?, ?)",
                (user_id, mode, query, datetime.now(timezone.utc).isoformat()),
            )
            query_id = cur.lastrowid
            assert query_id is not None
            conn.executemany(
                "INSERT INTO query_hits (query_id, file_id, title, category, rank, score)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (query_id, h.file_id, h.title, h.category, h.rank, h.score)
                    for h in unique
                ],
            )
        return query_id

    def record_answer(
        self, query_id: int, *, answer: str | None = None, error: str | None = None
    ) -> None:
        """Attach the LLM's answer (or the error that stopped it) to a logged query."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE queries SET answer = ?, error = ? WHERE id = ?",
                (answer, error, query_id),
            )

    # -- read ------------------------------------------------------------
    def monthly_counts(
        self,
        kind: Kind,
        months: int = DEFAULT_MONTHS,
        now: datetime | None = None,
    ) -> tuple[list[str], dict[str, list[int]]]:
        """Queries per month for each document (by file id) or category.

        Returns ``(month_keys, {key: counts})`` where every counts list is
        aligned with ``month_keys`` and zero-filled.
        """
        keys = month_keys(months, now)
        index = {k: i for i, k in enumerate(keys)}
        if kind == "document":
            column, extra = "h.file_id", " AND h.file_id IS NOT NULL"
        else:
            column, extra = "h.category", ""

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {column} AS key, substr(q.created_at, 1, 7) AS month,"
                "        COUNT(DISTINCT q.id) AS n"
                " FROM query_hits h JOIN queries q ON q.id = h.query_id"
                f" WHERE q.created_at >= ?{extra}"
                " GROUP BY key, month",
                (f"{keys[0]}-01",),
            ).fetchall()

        out: dict[str, list[int]] = {}
        for row in rows:
            slot = index.get(str(row["month"]))
            if slot is None:  # e.g. clock skew into a future month
                continue
            out.setdefault(str(row["key"]), [0] * len(keys))[slot] += int(row["n"])
        return keys, out

    def last_titles(self) -> dict[str, str]:
        """The most recently logged title of every file (label for deleted files)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT file_id, title FROM query_hits"
                " WHERE file_id IS NOT NULL ORDER BY query_id"
            ).fetchall()
        return {str(r["file_id"]): str(r["title"]) for r in rows}
