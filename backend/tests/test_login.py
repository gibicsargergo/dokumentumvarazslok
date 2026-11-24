
import pytest
import auth.store as auth_store

from auth.store import AuthStore
from auth.service import AuthService, InvalidCredentialsError


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(
        auth_store, "DB_PATH", tmp_path / "test_metadata.db"
    )

    return AuthService(AuthStore())


def test_successful_login(service):
    registered_user = service.register(
        "test@example.com",
        "TestPassword123!"
    )

    logged_in_user = service.login(
        "test@example.com",
        "TestPassword123!"
    )

    assert logged_in_user == registered_user


def test_incorrect_password(service):
    service.register(
        "test@example.com",
        "TestPassword123!"
    )

    with pytest.raises(InvalidCredentialsError):
        service.login("test@example.com", "wrongpassword")


def test_nonexistent_user(service):
    with pytest.raises(InvalidCredentialsError):
        service.login(
            "unknown@example.com",
            "TestPassword123!"
        )


def test_login_email_normalization(service):
    registered_user = service.register(
        "test@example.com",
        "TestPassword123!"
    )

    logged_in_user = service.login(
        "  TEST@Example.com  ",
        "TestPassword123!"
    )

    assert logged_in_user == registered_user
