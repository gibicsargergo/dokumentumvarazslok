from __future__ import annotations

import sys
from pathlib import Path

# Make sure `rag` imports resolve no matter where we're launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag import KnowledgeBase
from rag.document_file import SUPPORTED_EXTS


def _hr(char: str = "-", width: int = 60) -> None:
    print(char * width)


def cmd_add(kb: KnowledgeBase) -> None:
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

    for target in targets:
        try:
            result = kb.add(target, title=title, category=category, tags=tags)
            print(
                f"  + added {target.name}: id={result['id'][:8]} chunks={result['chunks']}"
            )
        except Exception as exc:
            print(f"  x failed {target.name}: {exc}")


def cmd_list(kb: KnowledgeBase) -> None:
    docs = kb.list_documents()
    if not docs:
        print("  (no documents stored yet)")
        return
    for i, d in enumerate(docs, 1):
        print(f"[{i}] {d['id'][:8]}  {d['title']}   (chunks={d['chunks']})")
        bits = []
        if d["category"]:
            bits.append(f"cat={d['category']}")
        if d["tags"]:
            bits.append("tags=" + ",".join(d["tags"]))
        if bits:
            print("      " + "  ".join(bits))
        if d["source"]:
            print(f"      src={d['source']}")


def cmd_delete(kb: KnowledgeBase) -> None:
    docs = kb.list_documents()
    if not docs:
        print("  (nothing to delete)")
        return
    print("Stored documents:")
    for i, d in enumerate(docs, 1):
        print(f"  [{i}] {d['id']}  {d['title']} (chunks={d['chunks']})")
    choice = input("Delete which number? ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(docs)):
        print("  ! invalid selection")
        return
    doc = docs[int(choice) - 1]
    removed = kb.delete(doc["id"])
    print(f"  - deleted {doc['title']} ({removed} chunks removed)")


def cmd_search(kb: KnowledgeBase) -> None:
    query = input("Query: ").strip()
    if not query:
        print("  (empty query)")
        return
    results = kb.search(query)
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
                cmd_add(kb)
            elif choice == "2":
                cmd_list(kb)
            elif choice == "3":
                cmd_delete(kb)
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
