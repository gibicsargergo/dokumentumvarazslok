
import pytest
import auth.store as auth_store

from auth.store import AuthStore
from auth.service import AuthService


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


def test_default_role(user):
    assert user.role == "user"


def test_promote_to_admin(service, user):
    assert service.store.set_user_role(user.id, "admin")

    updated_user = service.store.get_user_by_id(user.id)

    assert updated_user is not None
    assert updated_user.role == "admin"


def test_demote_to_user(service, user):
    service.store.set_user_role(user.id, "admin")
    service.store.set_user_role(user.id, "user")

    updated_user = service.store.get_user_by_id(user.id)

    assert updated_user is not None
    assert updated_user.role == "user"


def test_set_role_nonexistent_user(service):
    assert service.store.set_user_role(
        "nonexistent-id", "admin"
    ) is False


def test_invalid_role(service, user):
    with pytest.raises(ValueError, match="Invalid role"):
        service.store.set_user_role(user.id, "invalid")


def test_get_current_actor(service, user):
    token = service.create_session(user)
    actor = service.get_current_actor(token)

    assert actor is not None
    assert actor.user_id == user.id
    assert actor.role == "user"
    assert actor.is_admin is False


def test_get_admin_actor(service, user):
    service.store.set_user_role(user.id, "admin")

    token = service.create_session(user)
    actor = service.get_current_actor(token)

    assert actor is not None
    assert actor.is_admin is True


def test_get_actor_invalid_token(service):
    assert service.get_current_actor("invalid-token") is None


def test_role_change_during_session(service, user):
    token = service.create_session(user)

    service.store.set_user_role(user.id, "admin")

    actor = service.get_current_actor(token)

    assert actor is not None
    assert actor.is_admin is True
