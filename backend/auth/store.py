import sqlite3
from filestore.config import STORAGE_DIR, DB_NAME
import uuid
from datetime import datetime
from .models import User, Session, Role

DB_PATH = STORAGE_DIR / DB_NAME

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'admin'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);
"""


def initialize_auth_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)


class AuthStore:
    def __init__(self):
        initialize_auth_db()

    def create_user(self, email: str, password_hash: str) -> User:
        user_id = uuid.uuid4().hex
        email = email.strip().lower()

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, email, password_hash, "user"),
            )

        return User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            role="user",
        )

    def get_user_by_email(self, email: str) -> User | None:
        email = email.strip().lower()

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        if row is None:
            return None

        return User(**row)

    def get_user_by_id(self, user_id: str) -> User | None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return User(**row)
    
    def create_session(
        self,
        token_hash: str,
        user_id: str,
        expires_at: datetime,
    ) -> Session:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                INSERT INTO sessions (
                    token_hash, user_id, expires_at
                )
                VALUES (?, ?, ?)
                """,
                (token_hash, user_id, expires_at.isoformat()),
            )

        return Session(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
        )

    def get_session(self, token_hash: str) -> Session | None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()

        if row is None:
            return None

        return Session(
            token_hash=row["token_hash"],
            user_id=row["user_id"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
        )

    def delete_session(self, token_hash: str) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash,),
            )

    def set_user_role(self, user_id: str, role: Role) -> bool:
        if role not in ("user", "admin"):
            raise ValueError("Invalid role")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (role, user_id),
            )

        return cursor.rowcount > 0


