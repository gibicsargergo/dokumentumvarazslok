from __future__ import annotations

import re

from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _max_normalize(values: list[float]) -> list[float]:
    peak = max(values) if values else 0.0
    if peak <= 0:
        return [0.0] * len(values)
    return [v / peak for v in values]


class Reranker:
    def __init__(self, weights: dict[str, float]) -> None:
        self.weights = {"cosine": 0.3, "bm25": 0.4, "fuzzy": 0.3}
        self.weights.update(weights)

    def score(self, query: str, candidates: list[dict]) -> list[dict]:
        """Re-rank *candidates*.

        Each candidate must carry ``text`` and ``cos_sim`` (0..1); any extra keys
        (e.g. ``meta``) are passed through untouched. Returns copies sorted by the
        blended score (descending), each annotated with ``score``, ``bm25``,
        ``fuzzy`` and ``cosine``.
        """
        if not candidates:
            return []

        q_tokens = tokenize(query)
        corpus = [tokenize(c["text"]) for c in candidates]

        bm25_raw = [0.0] * len(candidates)
        if q_tokens and any(corpus):
            try:
                bm25 = BM25Okapi(corpus)
                bm25_raw = [float(x) for x in bm25.get_scores(q_tokens)]
            except ValueError:
                pass
        bm25_norm = _max_normalize(bm25_raw)

        w_cos = self.weights["cosine"]
        w_bm25 = self.weights["bm25"]
        w_fz = self.weights["fuzzy"]

        results: list[dict] = []
        for i, cand in enumerate(candidates):
            cos = max(0.0, min(1.0, float(cand.get("cos_sim", 0.0))))
            fz = fuzz.token_set_ratio(query, cand["text"]) / 100.0
            blended = w_cos * cos + w_bm25 * bm25_norm[i] + w_fz * fz
            item = dict(cand)
            item.update(
                {"score": blended, "bm25": bm25_raw[i], "fuzzy": fz, "cosine": cos}
            )
            results.append(item)

        results.sort(key=lambda r: r["score"], reverse=True)
        return results
