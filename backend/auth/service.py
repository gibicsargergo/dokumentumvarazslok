
import sqlite3

from .models import User
from .store import AuthStore
from .security import hash_password


class EmailAlreadyExistsError(ValueError):
    pass


class AuthService:
    def __init__(self, store: AuthStore):
        self.store = store

    def register(self, email: str, password: str) -> User:
        email = email.strip().lower()

        if not email or "@" not in email:
            raise ValueError("Invalid email address")

        if len(password) < 8:
            raise ValueError(
                "Password must be at least 8 characters long"
            )

        if self.store.get_user_by_email(email) is not None:
            raise EmailAlreadyExistsError("Email already registered")

        password_hash = hash_password(password)

        try:
            return self.store.create_user(email, password_hash)
        except sqlite3.IntegrityError:
            if self.store.get_user_by_email(email) is not None:
                raise EmailAlreadyExistsError(
                    "Email already registered"
                ) from None
            raise
