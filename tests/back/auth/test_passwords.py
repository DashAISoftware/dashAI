import pytest

from DashAI.back.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    hash_password,
    validate_password_length,
    verify_password,
)


def test_hash_verifies_only_the_right_password():
    hashed = hash_password("correct horse")

    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_hash_embeds_algorithm_and_cost():
    assert hash_password("abc12345").startswith("$2b$12$")


def test_same_password_gives_different_hashes():
    # A fresh salt per hash, so equal passwords are not visible in the database
    first = hash_password("abc12345")
    second = hash_password("abc12345")

    assert first != second
    assert verify_password("abc12345", first)
    assert verify_password("abc12345", second)


def test_password_at_the_limit_is_accepted():
    password = "a" * MAX_PASSWORD_LENGTH

    assert verify_password(password, hash_password(password))


@pytest.mark.parametrize(
    "password",
    [
        "a" * (MAX_PASSWORD_LENGTH + 1),
        # 40 characters but 80 bytes, over bcrypt's 72-byte limit
        "ñ" * 40,
    ],
)
def test_too_long_password_is_rejected(password):
    with pytest.raises(ValueError, match="at most"):
        validate_password_length(password)
    with pytest.raises(ValueError, match="at most"):
        hash_password(password)


def test_verify_fails_on_malformed_hash():
    assert not verify_password("abc12345", "not-a-bcrypt-hash")


def test_verify_fails_on_too_long_password():
    hashed = hash_password("abc12345")

    assert not verify_password("a" * 100, hashed)
