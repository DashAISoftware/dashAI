"""Authentication endpoints: account creation, login, logout and profile."""

import logging
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from kink import di, inject
from sqlalchemy import exc, or_, select

from DashAI.back.api.api_v1.schemas.auth_params import (
    ChangePasswordParams,
    LoginParams,
    ProfileUpdateParams,
    RegisterParams,
    RoleSummary,
    UserResponse,
)
from DashAI.back.auth.cookies import clear_auth_cookie, set_auth_cookie
from DashAI.back.auth.dependencies import (
    get_current_user,
    get_user_permissions,
    load_user,
)
from DashAI.back.auth.passwords import hash_password, verify_password
from DashAI.back.auth.tokens import create_access_token
from DashAI.back.dependencies.database.models import Role, User

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

router = APIRouter()

# Global role given to every new account
DEFAULT_ROLE_UID = "member"

# The endpoints that hash or verify passwords are plain functions (not async):
# bcrypt takes a fraction of a second on purpose, and FastAPI runs plain
# functions in a worker thread instead of blocking every other request.


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """Hash checked when the login user does not exist.

    Verifying a password against it takes as long as a real check, so the
    response time does not reveal which accounts exist.
    """
    return hash_password("dashai-dummy-password")


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        social_name=user.social_name,
        bio=user.bio,
        phone=user.phone,
        github=user.github,
        linkedin=user.linkedin,
        legal_name=user.legal_name,
        organization=user.organization,
        position=user.position,
        global_role=RoleSummary(uid=user.global_role.uid, name=user.global_role.name),
        permissions=sorted(get_user_permissions(user)),
        last_login=user.last_login,
        created=user.created,
    )


def _start_session(response: Response, user: User, config: Dict[str, Any]) -> None:
    token = create_access_token(user.id, user.token_version, di["auth_secret"])
    set_auth_cookie(response, token, secure=config["AUTH_COOKIE_SECURE"])


def _database_error(e: Exception) -> HTTPException:
    logger.exception(e)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal database error",
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@inject
def register(
    params: RegisterParams,
    response: Response,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Create an account with the default role and log it in."""
    with session_factory() as db:
        try:
            taken = db.execute(
                select(User.username, User.email).where(
                    or_(User.username == params.username, User.email == params.email)
                )
            ).first()
            if taken is not None:
                field = "username" if taken.username == params.username else "email"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"That {field} is already registered",
                )

            role = db.execute(
                select(Role).where(Role.uid == DEFAULT_ROLE_UID)
            ).scalar_one_or_none()
            if role is None:
                logger.error("Default role '%s' does not exist.", DEFAULT_ROLE_UID)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Accounts cannot be created yet",
                )

            user = User(
                username=params.username,
                email=params.email,
                password_hash=hash_password(params.password),
                social_name=params.social_name,
                global_role_id=role.id,
                last_login=datetime.now(),
            )
            db.add(user)
            db.commit()
        except HTTPException:
            raise
        except exc.IntegrityError as e:
            # Another request registered the same username or email meanwhile
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That username or email is already registered",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            raise _database_error(e) from e

        user = load_user(db, user.id)
        _start_session(response, user, config)
        return _to_response(user)


@router.post("/login", response_model=UserResponse)
@inject
def login(
    params: LoginParams,
    response: Response,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Check the credentials and start a session."""
    identifier = params.identifier.strip()
    # Emails are stored in lowercase; usernames keep their case
    if "@" in identifier:
        condition = User.email == identifier.lower()
    else:
        condition = User.username == identifier

    with session_factory() as db:
        try:
            user = db.execute(select(User).where(condition)).scalar_one_or_none()
            if user is None:
                verify_password(params.password, _dummy_hash())
                password_ok = False
            else:
                password_ok = verify_password(params.password, user.password_hash)

            # The same answer for an unknown account and a wrong password
            if not password_ok:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This account is disabled",
                )

            user.last_login = datetime.now()
            db.commit()
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            raise _database_error(e) from e

        user = load_user(db, user.id)
        _start_session(response, user, config)
        return _to_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
def logout(
    response: Response,
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """End the session in this browser."""
    clear_auth_cookie(response, secure=config["AUTH_COOKIE_SECURE"])


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
@inject
def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """End every session of the user, in every browser and device."""
    with session_factory() as db:
        try:
            user = db.get(User, current_user.id)
            # Every token issued before carries the old number
            user.token_version += 1
            db.commit()
        except exc.SQLAlchemyError as e:
            db.rollback()
            raise _database_error(e) from e
    clear_auth_cookie(response, secure=config["AUTH_COOKIE_SECURE"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the logged-in user."""
    return _to_response(current_user)


@router.patch("/me", response_model=UserResponse)
@inject
def update_me(
    params: ProfileUpdateParams,
    current_user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Update the profile fields the user is allowed to edit."""
    with session_factory() as db:
        try:
            user = db.get(User, current_user.id)
            # Only the fields present in the request are changed
            for field, value in params.model_dump(exclude_unset=True).items():
                setattr(user, field, value)
            db.commit()
        except exc.SQLAlchemyError as e:
            db.rollback()
            raise _database_error(e) from e

        return _to_response(load_user(db, current_user.id))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@inject
def change_password(
    params: ChangePasswordParams,
    response: Response,
    current_user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Change the password and end the sessions on other devices."""
    with session_factory() as db:
        try:
            user = db.get(User, current_user.id)
            if not verify_password(params.current_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The current password is incorrect",
                )
            user.password_hash = hash_password(params.new_password)
            # Invalidates the other sessions; this one gets a new token below
            user.token_version += 1
            db.commit()
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            raise _database_error(e) from e

        _start_session(response, user, config)
