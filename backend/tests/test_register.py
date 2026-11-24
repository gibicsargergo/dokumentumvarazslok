import pytest
import auth.store as auth_store

from auth.store import AuthStore
from auth.service import AuthService, EmailAlreadyExistsError
from auth.security import verify_password


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_store, "DB_PATH", tmp_path / "test_metadata.db")

    store = AuthStore()
    return AuthService(store)


def test_successful_registration(service):
    email = "register-test@example.com"
    password = "TestPassword123!"

    user = service.register(email, password)

    assert user.id
    assert user.email == email
    assert user.role == "user"
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)


def test_duplicate_registration(service):
    email = "register-test@example.com"
    password = "TestPassword123!"

    service.register(email, password)

    with pytest.raises(EmailAlreadyExistsError):
        service.register(email, password)


def test_invalid_password(service):
    with pytest.raises(ValueError, match="Password must be"):
        service.register("test@example.com", "abc")


def test_invalid_email(service):
    with pytest.raises(ValueError, match="Invalid email address"):
        service.register("invalid-email", "TestPassword123!")


def test_email_normalization(service):
    user = service.register("  TEST@Example.com  ", "TestPassword123!")

    assert user.email == "test@example.com"
