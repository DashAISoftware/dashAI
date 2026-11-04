from datetime import datetime, timedelta, timezone

import jwt
import pytest

from DashAI.back.auth.tokens import (
    ALGORITHM,
    TOKEN_LIFETIME,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)

SECRET = b"test-secret-with-at-least-32-bytes!!"


def test_token_roundtrip():
    token = create_access_token(7, 3, SECRET)
    data = decode_access_token(token, SECRET)

    assert data.user_id == 7
    assert data.token_version == 3
    assert data.jti


def test_each_token_has_its_own_id():
    first = decode_access_token(create_access_token(7, 0, SECRET), SECRET)
    second = decode_access_token(create_access_token(7, 0, SECRET), SECRET)

    assert first.jti != second.jti


def test_token_is_valid_until_it_expires():
    almost_expired = datetime.now(timezone.utc) - TOKEN_LIFETIME + timedelta(minutes=1)
    token = create_access_token(7, 0, SECRET, now=almost_expired)

    assert decode_access_token(token, SECRET).user_id == 7


def test_expired_token_is_rejected():
    expired = datetime.now(timezone.utc) - TOKEN_LIFETIME - timedelta(minutes=1)
    token = create_access_token(7, 0, SECRET, now=expired)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_token_signed_with_another_secret_is_rejected():
    token = create_access_token(7, 0, b"another-secret-with-at-least-32-bytes")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_tampered_token_is_rejected():
    token = create_access_token(7, 0, SECRET)
    header, payload, signature = token.split(".")
    # Payload of another user, keeping the original signature
    other = create_access_token(1, 0, SECRET).split(".")[1]

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{other}.{signature}", SECRET)


def test_unsigned_token_is_rejected():
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "7",
        "ver": 0,
        "jti": "x",
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    token = jwt.encode(claims, None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_token_missing_a_claim_is_rejected():
    now = datetime.now(timezone.utc)
    # No "ver": the token could not be revoked
    claims = {"sub": "7", "jti": "x", "iat": now, "exp": now + TOKEN_LIFETIME}
    token = jwt.encode(claims, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_token_with_non_numeric_subject_is_rejected():
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "admin",
        "ver": 0,
        "jti": "x",
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
    }
    token = jwt.encode(claims, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_garbage_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-token", SECRET)
