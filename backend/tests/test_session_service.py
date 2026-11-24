
from datetime import datetime, timedelta, timezone

import pytest
import auth.store as auth_store

from auth.store import AuthStore
from auth.service import AuthService
from auth.security import (
    generate_session_token,
    hash_session_token,
)


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        auth_store, "DB_PATH", tmp_path / "test_metadata.db"
    )

    return AuthService(AuthStore())


@pytest.fixture
def user(service):
    return service.register(
        "test@example.com",
        "TestPassword123!",
    )


def test_create_session(service, user):
    token = service.create_session(user)

    session = service.store.get_session(
        hash_session_token(token)
    )

    assert session is not None
    assert session.user_id == user.id


def test_session_duration(service, user):
    before = datetime.now(timezone.utc)

    token = service.create_session(user)

    after = datetime.now(timezone.utc)

    session = service.store.get_session(
        hash_session_token(token)
    )

    assert session is not None
    assert (
        before + timedelta(days=1)
        <= session.expires_at
        <= after + timedelta(days=1)
    )


def test_get_current_user(service, user):
    token = service.create_session(user)

    assert service.get_current_user(token) == user


def test_invalid_session_token(service):
    assert service.get_current_user("invalid-token") is None


def test_expired_session(service, user):
    token = generate_session_token()
    token_hash = hash_session_token(token)

    service.store.create_session(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert service.get_current_user(token) is None
    assert service.store.get_session(token_hash) is None


def test_logout(service, user):
    token = service.create_session(user)

    service.logout(token)

    assert service.get_current_user(token) is None
    assert service.store.get_session(
        hash_session_token(token)
    ) is None


def test_logout_invalid_token(service):
    service.logout("invalid-token")

    assert service.get_current_user("invalid-token") is None
