
import pytest
import auth.store as auth_store

from auth.store import AuthStore
from auth.cli import main


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


def test_promote_user(store, user, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["auth.cli", user.email, "admin"],
    )

    main()

    updated_user = store.get_user_by_id(user.id)

    assert updated_user is not None
    assert updated_user.role == "admin"


def test_demote_user(store, user, monkeypatch):
    store.set_user_role(user.id, "admin")

    monkeypatch.setattr(
        "sys.argv",
        ["auth.cli", user.email, "user"],
    )

    main()

    updated_user = store.get_user_by_id(user.id)

    assert updated_user is not None
    assert updated_user.role == "user"


def test_nonexistent_user(store, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["auth.cli", "unknown@example.com", "admin"],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1


def test_invalid_role(store, user, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["auth.cli", user.email, "invalid"],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2
