
import pytest
import auth.store as auth_store

from auth.store import AuthStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        auth_store, "DB_PATH", tmp_path / "test_metadata.db"
    )

    return AuthStore()


def test_create_user(store):
    user = store.create_user(
        email="test@example.com",
        password_hash="temporary-test-hash"
    )

    assert user.id
    assert user.email == "test@example.com"
    assert user.password_hash == "temporary-test-hash"
    assert user.role == "user"


def test_get_user_by_email(store):
    user = store.create_user(
        email="test@example.com",
        password_hash="temporary-test-hash"
    )

    assert store.get_user_by_email("test@example.com") == user


def test_get_user_by_id(store):
    user = store.create_user(
        email="test@example.com",
        password_hash="temporary-test-hash"
    )

    assert store.get_user_by_id(user.id) == user


def test_get_nonexistent_user_by_email(store):
    assert store.get_user_by_email("unknown@example.com") is None


def test_get_nonexistent_user_by_id(store):
    assert store.get_user_by_id("nonexistent-id") is None
