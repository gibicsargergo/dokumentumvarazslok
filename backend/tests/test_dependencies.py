
import pytest
import auth.store as auth_store

from fastapi import HTTPException

from auth.store import AuthStore
from auth.service import AuthService
from auth.dependencies import (
    require_user,
    require_actor,
    require_admin,
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


def test_require_user(service, user):
    token = service.create_session(user)

    result = require_user(
        session_token=token,
        service=service,
    )

    assert result == user


def test_require_user_missing_token(service):
    with pytest.raises(HTTPException) as exc:
        require_user(
            session_token=None,
            service=service,
        )

    assert exc.value.status_code == 401


def test_require_user_invalid_token(service):
    with pytest.raises(HTTPException) as exc:
        require_user(
            session_token="invalid-token",
            service=service,
        )

    assert exc.value.status_code == 401


def test_require_actor(user):
    actor = require_actor(user=user)

    assert actor.user_id == user.id
    assert actor.role == "user"


def test_require_admin_with_user(user):
    actor = require_actor(user=user)

    with pytest.raises(HTTPException) as exc:
        require_admin(actor=actor)

    assert exc.value.status_code == 403


def test_require_admin_with_admin(service, user):
    service.store.set_user_role(user.id, "admin")

    token = service.create_session(user)

    current_user = require_user(
        session_token=token,
        service=service,
    )

    actor = require_actor(user=current_user)

    assert require_admin(actor=actor) == actor
    assert actor.is_admin is True
