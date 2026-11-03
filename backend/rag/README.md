# rag — retrieval-augmented generation core

Self-contained Python package: ingests documents, chunks them, embeds with a
multilingual Sentence Transformer, stores in ChromaDB, and serves hybrid
semantic search results. No web framework dependency.

## Supported formats

| Extension | Extraction method |
|---|---|
| `.txt`, `.md` | Read as UTF-8 text |
| `.pdf` | pypdf per-page text extraction |
| `.jpg`, `.jpeg`, `.png`, `.webp` | EasyOCR (Hungarian + English) |

## Module layout

```
rag/
  __init__.py        # exports KnowledgeBase
  config.py          # all tunables: paths, model, chunk size, k, thresholds, weights
  document_file.py   # DocumentFile ABC → TextDocument / PdfDocument / ImageDocument + load()
  chunking.py        # cross-page sliding window over Block sequences
  embeddings.py      # Embedder static class (lazy MiniLM singleton, L2-normalized)
  reranker.py        # BM25Okapi + rapidfuzz token_set_ratio blended scorer
  db.py              # KnowledgeBase: add / delete / list_documents / search
```

## Programmatic use

```python
from rag import KnowledgeBase

kb = KnowledgeBase()

# Ingest (title/category/tags are optional metadata)
result = kb.add("path/to/doc.pdf", title="Bevezetés", category="előadás", tags=["cloud"])
print(result)  # {'id': 'abc123...', 'chunks': 6}

# Search
for hit in kb.search("Mik a felhő architektúra kihívásai?"):
    print(hit["score"], hit["title"], f"p{hit['page']}-{hit['page_end']}")
    print(hit["text"][:120])

# List all ingested documents
for doc in kb.list_documents():
    print(doc["title"], doc["chunks"])

# Remove a document (all its chunks + stored file)
kb.delete("abc123...")
```

## Search pipeline

```
embed query (MiniLM, 384-dim, L2-normalized)
  → ChromaDB cosine similarity → top-10 candidates
  → BM25 + fuzzy rerank (weighted blend: 0.3 cos + 0.4 bm25 + 0.3 fuzzy)
  → absolute floor: drop if cosine < RELEVANCE_THRESHOLD (default 0.35)
  → score-cliff: stop if next score < previous × SCORE_CLIFF_RATIO (default 0.5)
  → return up to RETURN_K (default 5) hits
```

Each result includes: `text`, `score`, `bm25`, `fuzzy`, `cosine`, `title`,
`category`, `tags`, `page`, `page_end`, `source`, `filename`, `doc_id`.

## Configuration

All parameters live in `config.py`:

| Constant | Default | Purpose |
|---|---|---|
| `EMBEDDING_MODEL` | paraphrase-multilingual-MiniLM-L12-v2 | Encoder for vectors |
| `EMBEDDING_DEVICE` | cpu | cpu or cuda |
| `CHUNK_SIZE` | 1600 | Characters per chunk |
| `CHUNK_OVERLAP` | 320 | Overlap between consecutive chunks |
| `TOP_K_CANDIDATES` | 10 | Cosine recall width before reranking |
| `RETURN_K` | 5 | Final results returned |
| `RELEVANCE_THRESHOLD` | 0.35 | Minimum cosine to keep a hit |
| `SCORE_CLIFF_RATIO` | 0.5 | Max relative score drop before stopping |
| `RERANK_WEIGHTS` | {cosine: 0.3, bm25: 0.4, fuzzy: 0.3} | Blend weights |
