"""The administration account every instance starts with.

Created on the first start so the instance has an administrator before anyone
registers. It is the only account that cannot be deleted, deactivated or lose
its role; the only way to lose access is forgetting its password.

Its password comes from the DASHAI_ADMIN_PASSWORD environment variable or,
when unset, is generated and written to a file only the owner can read, which
is deleted once the administrator changes it.
"""

import logging
import os
import secrets
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import or_, select

from DashAI.back.auth.passwords import hash_password
from DashAI.back.dependencies.database.models import Role, User

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

PASSWORD_ENV_VAR = "DASHAI_ADMIN_PASSWORD"
SYSTEM_ROLE_UID = "admin"


def _write_password_file(path: Path, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(password + "\n", encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        logger.warning("Could not restrict permissions on %s.", path)


def ensure_system_account(
    session_factory: "sessionmaker",
    config: Dict[str, Any],
    password: Optional[str] = None,
) -> None:
    """Create the administration account if the instance has none.

    Safe to run on every start: once the account exists nothing is changed,
    so a password or name changed later from the app is kept.

    Parameters
    ----------
    session_factory : sessionmaker
        Factory of database sessions.
    config : Dict[str, Any]
        Application config, with ``ADMIN_USERNAME``, ``ADMIN_EMAIL`` and
        ``ADMIN_PASSWORD_PATH``.
    password : Optional[str]
        Password to use instead of a generated one, by default the value of
        the DASHAI_ADMIN_PASSWORD environment variable.
    """
    if password is None:
        password = os.getenv(PASSWORD_ENV_VAR) or None

    username = config["ADMIN_USERNAME"]
    email = config["ADMIN_EMAIL"].strip().lower()
    password_path = Path(config["ADMIN_PASSWORD_PATH"])

    with session_factory() as db:
        if db.execute(select(User.id).where(User.is_system)).first() is not None:
            return

        # Never turns an existing account into the system one: whoever
        # registered that name or email would get the instance
        taken = db.execute(
            select(User.id).where(or_(User.username == username, User.email == email))
        ).first()
        if taken is not None:
            logger.error(
                "The administration account was not created: the username '%s' "
                "or the email '%s' already belong to another account. Set "
                "ADMIN_USERNAME and ADMIN_EMAIL to free values and restart.",
                username,
                email,
            )
            return

        role = db.execute(select(Role).where(Role.uid == SYSTEM_ROLE_UID)).scalar_one()

        generated = password is None
        if generated:
            password = secrets.token_urlsafe(18)

        db.add(
            User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                social_name="Administrador",
                global_role_id=role.id,
                is_system=True,
            )
        )

        # The file goes first: if it cannot be written, the account is not
        # created with a password nobody knows
        if generated:
            _write_password_file(password_path, password)
        try:
            db.commit()
        except Exception:
            db.rollback()
            if generated:
                password_path.unlink(missing_ok=True)
            raise

    if generated:
        logger.warning(
            "Created the administration account '%s'. Its password is in %s "
            "until it is changed from the app.",
            username,
            password_path,
        )
    else:
        logger.info(
            "Created the administration account '%s' with the password from %s.",
            username,
            PASSWORD_ENV_VAR,
        )


def forget_initial_password(config: Dict[str, Any]) -> None:
    """Delete the file with the generated password, once it no longer works."""
    Path(config["ADMIN_PASSWORD_PATH"]).unlink(missing_ok=True)
