# filestore — uploaded file storage

Stores the original uploaded documents (`.txt`, `.md`, `.pdf`, `.jpg`, `.jpeg`,
`.png`, `.webp`) on the local disk, with their metadata in a SQLite file.
It uses only the standard library, so there are no servers, containers or
credentials to share. It is independent of `rag`: uploading a file and
extracting/indexing its text are separate steps.

```
backend/storage/    (gitignored, shared with rag)
  <id><ext>         # the original file, e.g. 3f2a...c1.pdf
  metadata.db       # SQLite: files + file_labels tables
```

`rag` keeps its own copies in the same folder under its own ids; ids are
32-char uuids, so the two never collide.

## Metadata per file (`StoredFile`)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | uuid4 hex |
| `name` | `str` | display name / title (defaults to the original filename) |
| `original_filename` | `str` | name the file was uploaded with |
| `extension` | `str` | lower-case, e.g. `.pdf` |
| `category` | `str` | `""` when not set |
| `uploader` | `str` | `""` when not set |
| `uploaded_at` | `datetime` | timezone-aware UTC |
| `labels` | `tuple[str, ...]` | trimmed, de-duplicated, order kept |
| `size` | `int` | bytes |
| `path` | `Path` | where the original file lives (use for downloads) |
| `index_id` | `str \| None` | the file's `doc_id` in the search index; `None` if not indexed |

`StoredFile.to_dict()` returns a JSON-friendly dict.

## Usage

```python
from filestore import FileStore

fs = FileStore()  # defaults to backend/storage + backend/storage/metadata.db

# from a path ...
f = fs.save("docs/intro.pdf", uploader="alice", name="Bevezetés",
            category="előadás", labels=["cloud", "intro"])
# ... or from a binary stream (e.g. FastAPI UploadFile)
f = fs.save(upload.file, filename=upload.filename, uploader="bob")

fs.get(f.id)                                   # StoredFile | None
fs.list_files(category="előadás", label="cloud", uploader="alice")  # newest first
fs.update(f.id, name="Új cím", labels=["cloud"])  # None = leave unchanged
fs.delete(f.id)                                # True if it existed
```

Errors: an unsupported extension raises `UnsupportedFileType` (a
`ValueError`), and `update` on an unknown id raises `FileStoreError` (a
`LookupError`).

## Linking to the search index

After uploading, the caller (CLI now, FastAPI later) attempts indexing with
`rag.KnowledgeBase` and records the resulting document id:

```python
stored = fs.save(path, uploader="alice", category="előadás", labels=["cloud"])
result = kb.add(stored.path, title=stored.name, category=stored.category,
                tags=list(stored.labels))
if result["chunks"]:
    fs.update(stored.id, index_id=result["id"])

fs.get_by_index_id(hit["doc_id"])              # search hit -> uploaded file
kb.delete(stored.index_id); fs.delete(stored.id)  # delete both
```

The file stays in the store even if extraction finds no text (then `index_id`
stays `None`).
