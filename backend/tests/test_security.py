
from auth.security import hash_password, verify_password
from auth.security import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_session_token,
)


def test_hash_password():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_correct_password():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_incorrect_password():
    password = "TestPassword123!"
    hashed = hash_password(password)

    assert verify_password("wrongpassword", hashed) is False


def test_unique_password_hashes():
    password = "TestPassword123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_invalid_hash():
    assert verify_password("password", "invalid-hash") is False


def test_generate_session_token():
    token = generate_session_token()

    assert isinstance(token, str)
    assert len(token) >= 43


def test_unique_session_tokens():
    first_token = generate_session_token()
    second_token = generate_session_token()

    assert first_token != second_token


def test_hash_session_token():
    token = generate_session_token()
    hashed = hash_session_token(token)

    assert hashed != token
    assert len(hashed) == 64


def test_session_hash_consistency():
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)


def test_different_session_token_hashes():
    first_token = generate_session_token()
    second_token = generate_session_token()

    assert hash_session_token(first_token) != hash_session_token(second_token)
