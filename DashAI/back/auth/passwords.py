"""Password hashing with bcrypt."""

import bcrypt

# bcrypt only reads the first 72 bytes of a password and recent releases raise
# instead of truncating, so longer passwords are rejected up front
MAX_PASSWORD_LENGTH = 64
MAX_PASSWORD_BYTES = 72

# Work factor: each extra round doubles the time needed to compute a hash
BCRYPT_ROUNDS = 12


def validate_password_length(plain: str) -> None:
    """Raise ValueError when the password does not fit bcrypt's limits."""
    if (
        len(plain) > MAX_PASSWORD_LENGTH
        or len(plain.encode("utf-8")) > MAX_PASSWORD_BYTES
    ):
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."
        )


def hash_password(plain: str) -> str:
    """Hash a password with a fresh random salt.

    Parameters
    ----------
    plain : str
        The password as typed by the user.

    Returns
    -------
    str
        The bcrypt hash (``$2b$12$...``), which embeds the salt and the cost.
    """
    validate_password_length(plain)
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a password against a stored bcrypt hash.

    Parameters
    ----------
    plain : str
        The password as typed by the user.
    hashed : str
        The hash stored in ``user.password_hash``.

    Returns
    -------
    bool
        True if the password matches the hash.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Too long password or malformed hash: treat it as a failed login
        return False
