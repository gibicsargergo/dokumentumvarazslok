
from datetime import datetime, timedelta, timezone

import pytest
import sqlite3
import auth.store as auth_store

from auth.store import AuthStore
from auth.security import (
    generate_session_token,
    hash_session_token,
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        auth_store, "DB_PATH", tmp_path / "test_metadata.db"
    )

    return AuthStore()


@pytest.fixture
def user(store):
    return store.create_user(
        email="test@example.com",
        password_hash="temporary-test-hash",
    )


@pytest.fixture
def session(store, user):
    token_hash = hash_session_token(generate_session_token())
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    return store.create_session(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
    )


def test_create_session(store, user):
    token_hash = hash_session_token(generate_session_token())
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    session = store.create_session(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
    )

    assert session.token_hash == token_hash
    assert session.user_id == user.id
    assert session.expires_at == expires_at
    assert store.get_session(token_hash) == session


def test_get_session(store, session):
    assert store.get_session(session.token_hash) == session


def test_get_nonexistent_session(store):
    assert store.get_session("nonexistent-hash") is None


def test_delete_session(store, session):
    store.delete_session(session.token_hash)

    assert store.get_session(session.token_hash) is None


def test_delete_nonexistent_session(store):
    store.delete_session("nonexistent-hash")

    assert store.get_session("nonexistent-hash") is None


def test_session_with_nonexistent_user(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.create_session(
            token_hash=hash_session_token(generate_session_token()),
            user_id="nonexistent-user",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
