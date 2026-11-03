from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import EMBEDDING_DEVICE


@dataclass
class Block:
    text: str
    page: int | None = None


class UnsupportedFileType(ValueError):
    pass


class NotSupportedError(RuntimeError):
    pass


class DocumentFile(abc.ABC):
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.filename = self.path.name

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @abc.abstractmethod
    def read_blocks(self) -> list[Block]:
        """Return the document's readable content split into blocks."""

    def full_text(self) -> str:
        return "\n\n".join(b.text for b in self.read_blocks() if b.text.strip())


class TextDocument(DocumentFile):
    def read_blocks(self) -> list[Block]:
        text = self.path.read_text(encoding="utf-8", errors="replace")
        return [Block(text=text)] if text.strip() else []


class PdfDocument(DocumentFile):
    def read_blocks(self) -> list[Block]:
        from pypdf import PdfReader

        reader = PdfReader(str(self.path))
        blocks: list[Block] = []
        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                blocks.append(Block(text=text, page=index))
        return blocks


class ImageDocument(DocumentFile):
    _reader: Any = None  # easyocr.Reader instance (no type stubs shipped)

    @staticmethod
    def _get_reader() -> Any:
        """Lazily load the shared EasyOCR engine (hu + en)."""
        if ImageDocument._reader is None:
            import easyocr

            print("[ocr] loading EasyOCR models (hu+en) ...")
            ImageDocument._reader = easyocr.Reader(["hu", "en"], gpu=(EMBEDDING_DEVICE == "cuda"))
            print("[ocr] ready.")
        return ImageDocument._reader

    def read_blocks(self) -> list[Block]:
        reader = self._get_reader()
        results = reader.readtext(str(self.path))
        lines = [str(r[1]) for r in results if float(r[2]) > 0.3]
        text = "\n".join(lines).strip()
        return [Block(text=text)] if text else []


_EXT_MAP: dict[str, type[DocumentFile]] = {
    ".txt": TextDocument,
    ".md": TextDocument,
    ".pdf": PdfDocument,
    ".jpg": ImageDocument,
    ".jpeg": ImageDocument,
    ".png": ImageDocument,
    ".webp": ImageDocument,
}

SUPPORTED_EXTS = tuple(_EXT_MAP.keys())


def load(path: Path | str) -> DocumentFile:
    """Factory: pick the right :class:`DocumentFile` subclass by extension."""
    cls = _EXT_MAP.get(Path(path).suffix.lower())
    if cls is None:
        raise UnsupportedFileType(
            f"'{Path(path).name}' has an unsupported extension; "
            f"expected one of {', '.join(SUPPORTED_EXTS)}"
        )
    return cls(Path(path))
