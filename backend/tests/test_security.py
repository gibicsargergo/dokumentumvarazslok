
from auth.security import hash_password, verify_password


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
