"""FastAPI dependencies that resolve the logged-in user and check permissions."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, FrozenSet, Optional, Set, Union

from fastapi import Cookie, Depends, HTTPException, status
from kink import di
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from DashAI.back.auth.catalog import PROJECT_PERMISSIONS
from DashAI.back.auth.cookies import AUTH_COOKIE_NAME
from DashAI.back.auth.tokens import InvalidTokenError, decode_access_token
from DashAI.back.dependencies.database.models import (
    Project,
    Role,
    User,
    UserRoleProject,
)

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


@dataclass(frozen=True)
class ProjectAccess:
    """What the current user can do inside one project."""

    user: User
    project: Project
    # None when the user enters through ``projects.oversee`` without being
    # a member
    role: Optional[Role]
    permissions: FrozenSet[str]


def resolve_project_access(
    db: Session, user: User, project_id: int
) -> Optional[ProjectAccess]:
    """Return the user's access to a project, or None if the user has none.

    Inside a project only the project role counts: the global role does not
    add permissions there. The exception is ``projects.oversee``, which lets
    an administrator act on every project with all project permissions.
    """
    project = db.get(Project, project_id)
    if project is None:
        return None

    membership = db.execute(
        select(UserRoleProject)
        .options(selectinload(UserRoleProject.role).selectinload(Role.permissions))
        .where(
            UserRoleProject.user_id == user.id,
            UserRoleProject.project_id == project_id,
        )
    ).scalar_one_or_none()

    if "projects.oversee" in get_user_permissions(user):
        return ProjectAccess(
            user=user,
            project=project,
            role=membership.role if membership else None,
            permissions=frozenset(PROJECT_PERMISSIONS),
        )
    if membership is None:
        return None
    return ProjectAccess(
        user=user,
        project=project,
        role=membership.role,
        permissions=frozenset(p.uid for p in membership.role.permissions),
    )


def _project_not_found() -> HTTPException:
    # Projects the user cannot enter look the same as projects that do not
    # exist, so their names and ids do not leak
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found",
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action",
    )


def get_project_access(
    project_id: int,
    user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> ProjectAccess:
    """Return the current user's access to ``project_id``, or answer 404.

    ``project_id`` comes from the path, or from the query string when the
    route has no such path parameter.
    """
    with session_factory() as db:
        access = resolve_project_access(db, user, project_id)
    if access is None:
        raise _project_not_found()
    return access


def require_project_permission(permission_uid: str) -> Callable[..., ProjectAccess]:
    """Build a dependency that checks a permission inside the request's project.

    Usage:
    ``access: ProjectAccess = Depends(require_project_permission("datasets.write"))``.

    Parameters
    ----------
    permission_uid : str
        Uid of the required project permission, such as "datasets.write".

    Returns
    -------
    Callable[..., ProjectAccess]
        A dependency that returns the user's access to the project, answers
        404 if the user cannot enter it, or 403 if the role lacks the
        permission.
    """

    def dependency(
        access: ProjectAccess = Depends(get_project_access),
    ) -> ProjectAccess:
        if permission_uid not in access.permissions:
            raise _forbidden()
        return access

    return dependency


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
            raise _forbidden()
        return user

    return dependency
