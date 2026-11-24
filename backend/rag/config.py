import os
from pathlib import Path

# --- Paths ---------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent   # -> backend/
STORAGE_DIR = BACKEND_ROOT / "storage"                  # raw uploaded files
CHROMA_DIR = BACKEND_ROOT / "chroma_data"               # persistent ChromaDB

# --- Embeddings ----------------------------------------------------------
# Small multilingual encoder (~118M params): fast on CPU, handles HU + EN.
# Swap back to "BAAI/bge-m3" for max quality on a beefier box -- but you must
# re-index everything, since stored vectors are tied to their encoder.
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Query-side instruction prefix. This model uses none (""); kept configurable so
# instruction-tuned models (e.g. bge-m3) can opt in later without code changes.
QUERY_INSTRUCTION = ""
# Run on CPU by default -- safe across laptops with tiny/older GPUs. Set
# KB_EMBEDDING_DEVICE=cuda to opt into an accelerator you actually have room on.
EMBEDDING_DEVICE = os.environ.get("KB_EMBEDDING_DEVICE", "cpu")

# --- Chunking ------------------------------------------------------------
CHUNK_SIZE = 1600       # characters per chunk
CHUNK_OVERLAP = 320     # overlapping characters between consecutive chunks

# --- Retrieval / reranking ----------------------------------------------
TOP_K_CANDIDATES = 10            # how many vectors we recall before reranking
RETURN_K = 5                     # how many results we finally return
# Minimum cosine similarity to keep a candidate (a language-agnostic semantic
# floor). The BM25+fuzzy blend only re-orders survivors; it does not gate them,
# otherwise cross-language matches get starved when there are no shared keywords.
RELEVANCE_THRESHOLD = 0.35
RERANK_WEIGHTS = {"cosine": 0.3, "bm25": 0.4, "fuzzy": 0.3}
# Relative score cliff: stop collecting results once a candidate scores less than
# this fraction of the previous accepted result. Catches topic jumps mid-list.
SCORE_CLIFF_RATIO = 0.5

# --- Chroma ----------------------------------------------------------------
COLLECTION_NAME = "documents"
DISTANCE_METRIC = "cosine"
