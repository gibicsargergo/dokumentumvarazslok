from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import chromadb

from .chunking import sliding_window
from .config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DISTANCE_METRIC,
    RELEVANCE_THRESHOLD,
    RERANK_WEIGHTS,
    RETURN_K,
    SCORE_CLIFF_RATIO,
    STORAGE_DIR,
    TOP_K_CANDIDATES,
)
from .document_file import DocumentFile, load
from .embeddings import Embedder
from .reranker import Reranker


class KnowledgeBase:
    def __init__(
        self,
        storage_dir: Path | str = STORAGE_DIR,
        chroma_dir: Path | str = CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.chroma_path = Path(chroma_dir)

        self.client = chromadb.PersistentClient(path=str(self.chroma_path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": DISTANCE_METRIC},
        )
        self.reranker = Reranker(RERANK_WEIGHTS)

    # -- write -----------------------------------------------------------
    def add(
        self,
        path: Path | str,
        title: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Ingest one file: copy it to storage, extract, chunk, embed, store."""
        src = Path(path)
        doc: DocumentFile = load(src)  # raises on unsupported extension
        doc_id = uuid.uuid4().hex
        dest = self.storage / f"{doc_id}{src.suffix.lower()}"
        shutil.copyfile(str(src), dest)

        chunks = sliding_window(doc.read_blocks(), CHUNK_SIZE, CHUNK_OVERLAP)
        now = datetime.now(UTC).isoformat()
        texts: list[str] = []
        metadatas: list[chromadb.Metadata] = []
        for idx, (text, page_start, page_end) in enumerate(chunks):
            texts.append(text)
            metadatas.append(
                {
                    "doc_id": doc_id,
                    "title": title or doc.filename,
                    "category": category or "",
                    "tags": ",".join(tags or []),
                    "page_start": -1 if page_start is None else int(page_start),
                    "page_end": -1 if page_end is None else int(page_end),
                    "chunk_index": idx,
                    "source": str(dest),
                    "filename": doc.filename,
                    "created_at": now,
                }
            )

        if not texts:
            dest.unlink(missing_ok=True)
            return {"id": doc_id, "chunks": 0}

        vectors = Embedder.embed_texts(texts)
        ids = [f"{doc_id}:{i}" for i in range(len(texts))]
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=vectors.tolist(),
        )
        return {"id": doc_id, "chunks": len(texts)}

    # -- read ------------------------------------------------------------
    def delete(self, doc_id: str) -> int:
        """Remove every chunk belonging to *doc_id* plus its stored file."""
        existing = self.collection.get(where={"doc_id": doc_id})
        ids = existing.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        for file in self.storage.glob(f"{doc_id}*"):
            file.unlink(missing_ok=True)
        return len(ids)

    def list_documents(self) -> list[dict]:
        data = self.collection.get(include=["metadatas"])
        grouped: dict[str, dict] = {}
        for meta in data.get("metadatas") or []:
            doc_id = str(meta.get("doc_id", ""))
            entry = grouped.setdefault(
                doc_id,
                {
                    "id": doc_id,
                    "title": "",
                    "category": "",
                    "tags": [],
                    "chunks": 0,
                    "source": "",
                },
            )
            entry["title"] = meta.get("title", "")
            entry["category"] = meta.get("category", "")
            raw_tags = str(meta.get("tags", ""))
            entry["tags"] = [t for t in raw_tags.split(",") if t]
            entry["chunks"] += 1
            entry["source"] = meta.get("source", "")
        return list(grouped.values())

    def search(self, query: str, k: int | None = None) -> list[dict]:
        """Embed query -> cosine top-N -> BM25+fuzzy rerank -> top-k above threshold."""
        k = k or RETURN_K
        count = self.collection.count()
        if count == 0:
            return []

        qvec = Embedder.embed_query(query).tolist()
        n_results = min(TOP_K_CANDIDATES, count)
        res = self.collection.query(
            query_embeddings=[qvec],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        _docs = res["documents"]
        _metas = res["metadatas"]
        _dists = res["distances"]
        docs = _docs[0] if _docs else []
        metas = _metas[0] if _metas else []
        dists = _dists[0] if _dists else []

        candidates = [
            {"text": text, "meta": meta, "cos_sim": max(0.0, 1.0 - dist)}
            for text, meta, dist in zip(docs, metas, dists)
        ]

        ranked = self.reranker.score(query, candidates)

        out: list[dict] = []
        prev_score: float | None = None
        for item in ranked:
            if item["cosine"] < RELEVANCE_THRESHOLD:
                continue
            if prev_score is not None and item["score"] < prev_score * SCORE_CLIFF_RATIO:
                break
            meta = item["meta"]
            page_start = meta.get("page_start", -1)
            page_end = meta.get("page_end", -1)
            out.append(
                {
                    "text": item["text"],
                    "score": round(item["score"], 4),
                    "bm25": round(item["bm25"], 4),
                    "fuzzy": round(item["fuzzy"], 4),
                    "cosine": round(item["cosine"], 4),
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "tags": [t for t in (meta.get("tags", "").split(",")) if t],
                    "page": page_start if page_start >= 0 else None,
                    "page_end": page_end if page_end >= 0 else None,
                    "source": meta.get("source", ""),
                    "filename": meta.get("filename", ""),
                    "doc_id": meta.get("doc_id", ""),
                }
            )
            prev_score = item["score"]
            if len(out) >= k:
                break
        return out
