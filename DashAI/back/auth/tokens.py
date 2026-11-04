"""Signed session tokens (JWT)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Union

import jwt

ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(hours=10)


class InvalidTokenError(Exception):
    """The token is malformed, was tampered with or has expired."""


@dataclass(frozen=True)
class TokenData:
    """Claims read from a valid token."""

    user_id: int
    token_version: int
    jti: str


def create_access_token(
    user_id: int,
    token_version: int,
    secret: bytes,
    now: Union[datetime, None] = None,
) -> str:
    """Create a signed token for a user.

    Parameters
    ----------
    user_id : int
        Id of the user the token belongs to.
    token_version : int
        Current ``user.token_version``; bumping it invalidates this token.
    secret : bytes
        Signing key.
    now : Union[datetime, None]
        Issue time, only overridden by tests. Defaults to the current time.

    Returns
    -------
    str
        The encoded token.
    """
    issued_at = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "jti": uuid.uuid4().hex,
        "iat": issued_at,
        "exp": issued_at + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: bytes) -> TokenData:
    """Verify a token's signature and expiry and return its claims.

    Parameters
    ----------
    token : str
        The encoded token.
    secret : bytes
        Signing key.

    Returns
    -------
    TokenData
        The user id, token version and token id carried by the token.

    Raises
    ------
    InvalidTokenError
        If the token is malformed, tampered with or expired.
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "ver", "jti", "iat", "exp"]},
        )
        return TokenData(
            user_id=int(payload["sub"]),
            token_version=int(payload["ver"]),
            jti=payload["jti"],
        )
    except (jwt.InvalidTokenError, ValueError) as e:
        raise InvalidTokenError(str(e)) from e
