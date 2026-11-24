from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent  # -> backend/
STORAGE_DIR = BACKEND_ROOT / "storage"                 # uploaded originals + metadata.db
DB_NAME = "metadata.db"

# Text, PDF and rasterized images (see AGENTS.md).
ALLOWED_EXTENSIONS: tuple[str, ...] = (
    ".txt",
    ".md",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
)
