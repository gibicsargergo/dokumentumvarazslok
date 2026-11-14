from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from .db import KnowledgeBase


def __getattr__(name: str) -> Any:
    # PEP 562 lazy export so ``import rag`` stays cheap.
    if name == "KnowledgeBase":
        from .db import KnowledgeBase

        return KnowledgeBase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["KnowledgeBase"]
