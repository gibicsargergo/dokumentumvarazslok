from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "admin"]


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    role: Role = "user"