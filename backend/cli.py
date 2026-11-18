from __future__ import annotations

import sys
from pathlib import Path

# Make sure `rag` imports resolve no matter where we're launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from filestore import Actor, FileStore
from rag import KnowledgeBase
from rag.document_file import SUPPORTED_EXTS

# The CLI is a local maintenance tool, so it runs with admin rights.
CLI_ACTOR = Actor(user_id="cli", role="admin")


def _hr(char: str = "-", width: int = 60) -> None:
    print(char * width)


def cmd_add(kb: KnowledgeBase, files: FileStore) -> None:
    path = input("Path to a file or folder: ").strip()
    p = Path(path).expanduser()
    if not p.exists():
        print(f"  ! '{p}' does not exist.")
        return

    if p.is_dir():
        targets = [
            f
            for f in sorted(p.iterdir())
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
        ]
    else:
        targets = [p]

    if not targets:
        print("  ! no supported files found (.txt/.md/.pdf; images are stubbed)")
        return

    title = input("Title (optional): ").strip() or None
    category = input("Category (optional): ").strip() or None
    tags_raw = input("Tags, comma separated (optional): ").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None
    uploader_id = input(f"Uploader id [{CLI_ACTOR.user_id}]: ").strip() or CLI_ACTOR.user_id
    is_private = input("Private? [y/N]: ").strip().lower() in ("y", "yes")

    for target in targets:
        _upload_one(kb, files, target, title, category, tags, uploader_id, is_private)


def _upload_one(
    kb: KnowledgeBase,
    files: FileStore,
    target: Path,
    title: str | None,
    category: str | None,
    tags: list[str] | None,
    uploader_id: str,
    is_private: bool,
) -> None:
    # 1) upload: store the original file with its metadata
    try:
        stored = files.save(
            target,
            uploader_id=uploader_id,
            name=title,
            category=category or "",
            labels=tags or [],
            is_private=is_private,
        )
    except Exception as exc:
        print(f"  x failed to store {target.name}: {exc}")
        return

    # 2) attempt text extraction + indexing; the stored file is kept either way
    try:
        result = kb.add(
            stored.path,
            title=stored.name,
            category=stored.category,
            tags=list(stored.labels),
            uploader_id=stored.uploader_id,
            is_private=stored.is_private,
        )
    except Exception as exc:
        print(f"  ~ stored {target.name} (id={stored.id[:8]}) but indexing failed: {exc}")
        return
    if result["chunks"]:
        files.set_index_id(stored.id, result["id"])
    print(f"  + added {target.name}: id={stored.id[:8]} chunks={result['chunks']}")


def cmd_list(kb: KnowledgeBase, files: FileStore) -> None:
    stored = files.list_files(viewer=CLI_ACTOR)
    if not stored:
        print("  (no documents stored yet)")
        return
    chunks = {d["id"]: d["chunks"] for d in kb.list_documents()}
    for i, f in enumerate(stored, 1):
        n = chunks.get(f.index_id, 0) if f.index_id else 0
        print(f"[{i}] {f.id[:8]}  {f.name}   (chunks={n})")
        bits = [
            f"uploaded={f.uploaded_at:%Y-%m-%d %H:%M}",
            f"by={f.uploader_id}",
            "private" if f.is_private else "public",
        ]
        if f.category:
            bits.append(f"cat={f.category}")
        if f.labels:
            bits.append("labels=" + ",".join(f.labels))
        print("      " + "  ".join(bits))
        print(f"      file={f.path}")


def cmd_delete(kb: KnowledgeBase, files: FileStore) -> None:
    stored = files.list_files(viewer=CLI_ACTOR)
    if not stored:
        print("  (nothing to delete)")
        return
    print("Stored documents:")
    for i, f in enumerate(stored, 1):
        print(f"  [{i}] {f.id}  {f.name}")
    choice = input("Delete which number? ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(stored)):
        print("  ! invalid selection")
        return
    f = stored[int(choice) - 1]
    removed = kb.delete(f.index_id) if f.index_id else 0
    files.delete(f.id, actor=CLI_ACTOR)
    print(f"  - deleted {f.name} ({removed} chunks removed)")


def cmd_search(kb: KnowledgeBase) -> None:
    query = input("Query: ").strip()
    if not query:
        print("  (empty query)")
        return
    results = kb.search(query, viewer_id=CLI_ACTOR.user_id, see_all=CLI_ACTOR.is_admin)
    if not results:
        print("  ~ no results above the relevance threshold.")
        return
    for i, r in enumerate(results, 1):
        _hr("=")
        header = f"[{i}] score={r['score']}  {r['title']}"
        if r["page"] is not None:
            header += f"  (page {r['page']})"
        print(header)
        snippet = r["text"].replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:240].rstrip() + "..."
        print(f"    {snippet}")
        print(f"    source: {r['source']}")


def main() -> None:
    print("Knowledge Base CLI")
    _hr()
    kb = KnowledgeBase()
    files = FileStore()
    while True:
        print("\nWhat would you like to do?")
        print("  [1] Add documents")
        print("  [2] List documents")
        print("  [3] Delete a document")
        print("  [4] Search")
        print("  [5] Exit")
        choice = input("> ").strip()
        try:
            if choice == "1":
                cmd_add(kb, files)
            elif choice == "2":
                cmd_list(kb, files)
            elif choice == "3":
                cmd_delete(kb, files)
            elif choice == "4":
                cmd_search(kb)
            elif choice == "5":
                print("bye")
                break
            else:
                print("  ? pick 1-5")
        except KeyboardInterrupt:
            print("\n(interrupted, back to menu)")


if __name__ == "__main__":
    main()
