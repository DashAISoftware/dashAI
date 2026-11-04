"""FastAPI dependencies that resolve the logged-in user and check permissions."""

from typing import TYPE_CHECKING, Callable, Set, Union

from fastapi import Cookie, Depends, HTTPException, status
from kink import di
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from DashAI.back.auth.cookies import AUTH_COOKIE_NAME
from DashAI.back.auth.tokens import InvalidTokenError, decode_access_token
from DashAI.back.dependencies.database.models import Role, User

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker


def load_user(db: Session, user_id: int) -> Union[User, None]:
    """Load a user together with its global role and that role's permissions.

    The relationships are loaded eagerly so they stay readable after the
    session that loaded them is closed.
    """
    return db.execute(
        select(User)
        .options(selectinload(User.global_role).selectinload(Role.permissions))
        .where(User.id == user_id)
    ).scalar_one_or_none()


def get_user_permissions(user: User) -> Set[str]:
    """Return the uids of the permissions granted by the user's global role.

    Project roles are not included: they only apply inside their project.
    """
    return {permission.uid for permission in user.global_role.permissions}


def _unauthorized() -> HTTPException:
    # Same message for every failure, so a client cannot tell them apart
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user(
    session_token: Union[str, None] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    secret: bytes = Depends(lambda: di["auth_secret"]),
) -> User:
    """Return the user that owns the session cookie, or answer 401.

    The token only proves who the user is; whether the user is still active,
    whether the token was revoked and which permissions apply are read from
    the database on every request, so those changes take effect immediately.
    """
    if session_token is None:
        raise _unauthorized()

    try:
        token_data = decode_access_token(session_token, secret)
    except InvalidTokenError:
        raise _unauthorized() from None

    with session_factory() as db:
        user = load_user(db, token_data.user_id)

    if (
        user is None
        or not user.is_active
        or user.token_version != token_data.token_version
    ):
        raise _unauthorized()
    return user


def require_permission(permission_uid: str) -> Callable[..., User]:
    """Build a dependency that only lets users with a permission through.

    Usage: ``user: User = Depends(require_permission("users.manage"))``.

    Parameters
    ----------
    permission_uid : str
        Uid of the required permission, such as "users.manage".

    Returns
    -------
    Callable[..., User]
        A dependency that returns the current user or answers 403.
    """

    def dependency(user: User = Depends(get_current_user)) -> User:
        if permission_uid not in get_user_permissions(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency
