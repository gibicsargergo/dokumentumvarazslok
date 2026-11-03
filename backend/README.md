# Backend – document knowledge base

Python backend for a document-based knowledge base system.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install chromadb sentence-transformers pypdf rank-bm25 rapidfuzz easyocr
```

First run downloads the embedding model (~470 MB) and OCR models (~100 MB);
both cache locally afterward. Runs on CPU by default; set
`KB_EMBEDDING_DEVICE=cuda` to opt into a GPU.

## Use the CLI

```bash
python cli.py
```

Menu: `[1]` add files/folders · `[2]` list documents · `[3]` delete · `[4]` search

## Structure

```
backend/
  cli.py               # interactive menu entrypoint
  pyproject.toml       # package metadata
  pyrightconfig.json   # type-checker config (strict, venv-pinned)
  rag/                 # RAG core — see rag/README.md
  storage/             # raw uploaded files (runtime, gitignored)
  chroma_data/         # persistent ChromaDB (runtime, gitignored)
```
