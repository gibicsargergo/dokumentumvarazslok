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
| `uploader_id` | `str` | id of the authenticated uploader; required, **immutable** (a SQLite trigger rejects changes) |
| `uploaded_at` | `datetime` | timezone-aware UTC |
| `labels` | `tuple[str, ...]` | trimmed, de-duplicated, order kept |
| `size` | `int` | bytes |
| `path` | `Path` | where the original file lives (use for downloads) |
| `is_private` | `bool` | `False` (public) unless set at upload or by an admin |
| `index_id` | `str \| None` | the file's `doc_id` in the search index; `None` if not indexed |

`StoredFile.to_dict()` returns a JSON-friendly dict.

## Permissions

Callers identify themselves with an `Actor(user_id, role)` where `role` is
`"user"` or `"admin"`. The rules live in `filestore/permissions.py`:

| Action | Admin | Uploader | Other user |
|---|---|---|---|
| See / list / download a public file | ✅ | ✅ | ✅ |
| See / list / download a private file | ✅ | ✅ | ❌ |
| Edit metadata or visibility (`update`) | ✅ | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ |

- Read methods (`get`, `get_by_index_id`, `list_files`) take `viewer=`; a file
  the viewer may not see is treated as missing (`None` / left out), so its
  existence is not revealed. `viewer=None` means trusted internal access with
  no filtering — **request handlers must always pass the authenticated actor.**
- `update` and `delete` require `actor=` and raise `PermissionDenied` (a
  `PermissionError`) for non-admins.
- `set_index_id` / `clear_index_id` are system bookkeeping and take no actor.

## Usage

```python
from filestore import Actor, FileStore

fs = FileStore()  # defaults to backend/storage + backend/storage/metadata.db
alice = Actor("alice")                 # role defaults to "user"
admin = Actor("root", role="admin")

# from a path ...
f = fs.save("docs/intro.pdf", uploader_id=alice.user_id, name="Bevezetés",
            category="előadás", labels=["cloud", "intro"])          # public
# ... or from a binary stream (e.g. FastAPI UploadFile)
f = fs.save(upload.file, filename=upload.filename,
            uploader_id=alice.user_id, is_private=True)

fs.get(f.id, viewer=alice)                     # StoredFile | None
fs.list_files(viewer=alice, category="előadás", label="cloud")  # newest first
fs.update(f.id, actor=admin, name="Új cím", is_private=False)  # None = unchanged
fs.delete(f.id, actor=admin)                   # True if it existed
```

Errors: an unsupported extension raises `UnsupportedFileType` (a
`ValueError`), `update` on an unknown (or invisible) id raises
`FileStoreError` (a `LookupError`), and a disallowed edit/delete raises
`PermissionDenied`.

## Linking to the search index

After uploading, the caller (CLI now, FastAPI later) attempts indexing with
`rag.KnowledgeBase` and records the resulting document id:

```python
stored = fs.save(path, uploader_id=alice.user_id, category="előadás", labels=["cloud"])
result = kb.add(stored.path, title=stored.name, category=stored.category,
                tags=list(stored.labels),
                uploader_id=stored.uploader_id, is_private=stored.is_private)
if result["chunks"]:
    fs.set_index_id(stored.id, result["id"])

hits = kb.search(q, viewer_id=actor.user_id, see_all=actor.is_admin)
fs.get_by_index_id(hit["doc_id"], viewer=actor)   # search hit -> uploaded file

# changing visibility: update both sides
f = fs.update(stored.id, actor=admin, is_private=True)
if f.index_id:
    kb.set_visibility(f.index_id, f.is_private)

# renaming / recategorizing / relabeling: update both sides
f = fs.update(
    stored.id,
    actor=admin,
    name="Új cím",
    category="előadás",
    labels=["cloud", "intro"],
)
if f.index_id:
    kb.update_metadata(f.index_id, title=f.name, category=f.category, tags=list(f.labels))

kb.delete(stored.index_id); fs.delete(stored.id, actor=admin)  # delete both
```

The file stays in the store even if extraction finds no text (then `index_id`
stays `None`). Every chunk carries `uploader_id` and `is_private`, and
`kb.search` filters on them inside the vector query, so private documents
never use up candidate slots for users who can't see them. Downloads must go
through `fs.get(..., viewer=actor)`, never through a hit's `source` path.
