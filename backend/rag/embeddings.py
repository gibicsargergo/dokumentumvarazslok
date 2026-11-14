from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_DEVICE, EMBEDDING_MODEL, QUERY_INSTRUCTION


class Embedder:
    _model: SentenceTransformer | None = None

    @staticmethod
    def get_model() -> SentenceTransformer:
        """Load the model once and reuse it across calls. Picks cuda if it can"""
        if Embedder._model is not None:
            return Embedder._model

        if EMBEDDING_DEVICE != "cuda":
            os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        from sentence_transformers import SentenceTransformer

        print(f"[embeddings] loading '{EMBEDDING_MODEL}' on {EMBEDDING_DEVICE} ...")
        Embedder._model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
        print("[embeddings] ready.")
        return Embedder._model

    @staticmethod
    def embed_texts(texts: list[str]) -> np.ndarray:
        """Embed a batch of passages. Vectors are L2-normalized (cosine-friendly)."""
        import numpy as np

        if not texts:
            return np.zeros((0,), dtype="float32")
        vecs = Embedder.get_model().encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 20,
        )
        return np.asarray(vecs, dtype="float32")

    @staticmethod
    def embed_query(query: str) -> np.ndarray:
        """Embed a single query, prepending the configured instruction (if any)."""
        text = f"{QUERY_INSTRUCTION}{query}" if QUERY_INSTRUCTION else query
        return Embedder.embed_texts([text])[0]
