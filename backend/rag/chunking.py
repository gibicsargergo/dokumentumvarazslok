from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .document_file import Block


def sliding_window(
    blocks: Sequence[Block],
    size: int = 1600,
    overlap: int = 320,
) -> list[tuple[str, int | None, int | None]]:
    """Join *blocks* into one stream, then slide a ~*size*-char window over it.

    Returns de-duplicated ``(text, page_start, page_end)`` tuples; page bounds are
    ``None`` when the source has no notion of pages. Empty input -> [].
    """
    texts = [b.text for b in blocks]
    pages = [b.page for b in blocks]
    if not texts or not any(t.strip() for t in texts):
        return []

    parts: list[str] = []
    starts: list[int] = []
    pos = 0
    for i, t in enumerate(texts):
        sep_len = 2 if i else 0
        pos += sep_len
        starts.append(pos)
        parts.append("\n\n" if i else "")
        parts.append(t)
        pos += sep_len + len(t)
    joined = "".join(parts)
    n = len(joined)
    ranges = [
        (starts[i], starts[i] + len(texts[i]), pages[i]) for i in range(len(texts))
    ]

    if size <= 0:
        text = joined.strip()
        if not text:
            return []
        ps, pe = _page_bounds(ranges, 0, n)
        return [(text, ps, pe)]

    if overlap >= size:
        overlap = max(size // 2, 1)
    step = size - overlap

    seen: set[str] = set()
    out: list[tuple[str, int | None, int | None]] = []
    start = 0
    while start < n:
        end = min(start + size, n)
        piece = joined[start:end].strip()
        if piece and piece not in seen:
            seen.add(piece)
            ps, pe = _page_bounds(ranges, start, end)
            out.append((piece, ps, pe))
        if end == n:
            break
        start += step
    return out


def _page_bounds(
    ranges: list[tuple[int, int, int | None]], start: int, end: int
) -> tuple[int | None, int | None]:
    lo: int | None = None
    hi: int | None = None
    for bs, be, page in ranges:
        if be > start and bs < end and page is not None:
            lo = page if lo is None or page < lo else lo
            hi = page if hi is None or page > hi else hi
    return lo, hi
