
import sqlite3

from .models import User
from .store import AuthStore
from datetime import datetime, timedelta, timezone
from .security import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_session_token,
)

SESSION_DURATION = timedelta(days=1)

class EmailAlreadyExistsError(ValueError):
    pass

class InvalidCredentialsError(ValueError):
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

    def login(self, email: str, password: str) -> User:
        email = email.strip().lower()

        user = self.store.get_user_by_email(email)

        if user is None:
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(
                "Invalid email or password"
            )

        return user
    
    def create_session(self, user: User) -> str:
        token = generate_session_token()
        token_hash = hash_session_token(token)

        expires_at = datetime.now(timezone.utc) + SESSION_DURATION

        self.store.create_session(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires_at,
        )

        return token
    
    def get_current_user(self, token: str) -> User | None:
        token_hash = hash_session_token(token)
        session = self.store.get_session(token_hash)

        if session is None:
            return None

        if session.expires_at <= datetime.now(timezone.utc):
            self.store.delete_session(token_hash)
            return None

        return self.store.get_user_by_id(session.user_id)
    
    def logout(self, token: str) -> None:
        token_hash = hash_session_token(token)
        self.store.delete_session(token_hash)



