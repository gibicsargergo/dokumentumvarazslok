"""Who may do what with a stored file.

Rules (see AGENTS.md):

* public files are visible to every authenticated user;
* private files are visible only to their uploader and to admins;
* only admins may edit metadata or delete files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import StoredFile

Role = Literal["user", "admin"]


class PermissionDenied(PermissionError):
    """Raised when an actor is not allowed to perform an action on a file."""


@dataclass(frozen=True)
class Actor:
    """The authenticated user performing an action."""

    user_id: str
    role: Role = "user"

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("Actor.user_id must not be empty")
        if self.role not in ("user", "admin"):
            raise ValueError(f"unknown role '{self.role}'")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def can_view(actor: Actor, file: StoredFile) -> bool:
    return not file.is_private or actor.is_admin or actor.user_id == file.uploader_id


def can_edit(actor: Actor, file: StoredFile) -> bool:  # noqa: ARG001 - owner rules may come later
    return actor.is_admin


def can_delete(actor: Actor, file: StoredFile) -> bool:  # noqa: ARG001 - owner rules may come later
    return actor.is_admin
