from dataclasses import dataclass
from typing import Literal
from datetime import datetime

Role = Literal["user", "admin"]


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    role: Role = "user"

@dataclass(frozen=True)
class Session:
    token_hash: str
    user_id: str
    expires_at: datetime