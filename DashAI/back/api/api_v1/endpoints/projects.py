"""Project endpoints: create projects, list them and manage their members.

Any logged-in user can create a project and becomes its owner. Managing
members needs ``projects.manage`` inside the project, and only owners (or an
administrator) can give or take away the owner role. A project always keeps
at least one owner.
"""

import logging
from typing import TYPE_CHECKING, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from kink import di
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from DashAI.back.api.api_v1.schemas.auth_params import RoleSummary
from DashAI.back.api.api_v1.schemas.project_params import (
    MemberAddParams,
    MemberResponse,
    MemberRoleParams,
    ProjectCreateParams,
    ProjectResponse,
)
from DashAI.back.auth.catalog import PROJECT_PERMISSIONS
from DashAI.back.auth.dependencies import (
    ProjectAccess,
    get_current_user,
    get_project_access,
    get_user_permissions,
    require_project_permission,
)
from DashAI.back.dependencies.database.models import (
    Project,
    Role,
    User,
    UserRoleProject,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

router = APIRouter()

OWNER_ROLE_UID = "owner"


def _role_summary(role: Role) -> RoleSummary:
    return RoleSummary(uid=role.uid, name=role.name)


def _member_counts(db: Session, project_ids: List[int]) -> Dict[int, int]:
    rows = db.execute(
        select(UserRoleProject.project_id, func.count())
        .where(UserRoleProject.project_id.in_(project_ids))
        .group_by(UserRoleProject.project_id)
    ).all()
    return dict(rows)


def _to_response(access: ProjectAccess, member_count: int) -> ProjectResponse:
    project = access.project
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created=project.created,
        member_count=member_count,
        my_role=_role_summary(access.role) if access.role else None,
        my_permissions=sorted(access.permissions),
    )


def _project_role(db: Session, role_uid: str) -> Role:
    """Return a project-scoped role by uid, or answer 422."""
    role = db.execute(
        select(Role).where(Role.uid == role_uid, Role.scope == "project")
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown project role",
        )
    return role


def _membership(db: Session, project_id: int, user_id: int) -> UserRoleProject:
    membership = db.execute(
        select(UserRoleProject)
        .options(selectinload(UserRoleProject.role))
        .where(
            UserRoleProject.project_id == project_id,
            UserRoleProject.user_id == user_id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    return membership


def _check_can_handle_owners(access: ProjectAccess) -> None:
    """Only owners and administrators can give or take away the owner role.

    Otherwise a role with ``projects.manage`` could promote itself or demote
    the owners.
    """
    is_owner = access.role is not None and access.role.uid == OWNER_ROLE_UID
    if not is_owner and "projects.oversee" not in get_user_permissions(access.user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an owner can change who owns the project",
        )


def _check_keeps_an_owner(db: Session, membership: UserRoleProject) -> None:
    """Answer 409 if ``membership`` is the project's last owner."""
    if membership.role.uid != OWNER_ROLE_UID:
        return
    owners = db.execute(
        select(func.count())
        .select_from(UserRoleProject)
        .join(Role)
        .where(
            UserRoleProject.project_id == membership.project_id,
            Role.uid == OWNER_ROLE_UID,
        )
    ).scalar_one()
    if owners <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project must keep at least one owner",
        )


def _member_response(membership: UserRoleProject) -> MemberResponse:
    return MemberResponse(
        user_id=membership.user.id,
        username=membership.user.username,
        social_name=membership.user.social_name,
        role=_role_summary(membership.role),
        joined=membership.created,
    )


# Projects


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    params: ProjectCreateParams,
    user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a project with the current user as its owner."""
    with session_factory() as db:
        owner_role = _project_role(db, OWNER_ROLE_UID)
        project = Project(
            name=params.name,
            description=params.description,
            created_by_id=user.id,
        )
        project.members.append(UserRoleProject(user_id=user.id, role=owner_role))
        db.add(project)
        db.commit()
        db.refresh(project)

        access = ProjectAccess(
            user=user,
            project=project,
            role=owner_role,
            permissions=frozenset(p.uid for p in owner_role.permissions),
        )
        return _to_response(access, member_count=1)


@router.get("/", response_model=List[ProjectResponse])
def list_my_projects(
    user: User = Depends(get_current_user),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """List the projects the current user is a member of.

    Administrators only see their own projects here too; overseeing every
    project belongs to the administration views.
    """
    with session_factory() as db:
        memberships = (
            db.execute(
                select(UserRoleProject)
                .join(Project)
                .options(
                    selectinload(UserRoleProject.project),
                    selectinload(UserRoleProject.role).selectinload(Role.permissions),
                )
                .where(
                    UserRoleProject.user_id == user.id,
                    Project.is_archived.is_(False),
                )
                .order_by(Project.name)
            )
            .scalars()
            .all()
        )
        counts = _member_counts(db, [m.project_id for m in memberships])
        oversees = "projects.oversee" in get_user_permissions(user)

        return [
            _to_response(
                ProjectAccess(
                    user=user,
                    project=m.project,
                    role=m.role,
                    permissions=frozenset(
                        PROJECT_PERMISSIONS
                        if oversees
                        else [p.uid for p in m.role.permissions]
                    ),
                ),
                member_count=counts.get(m.project_id, 0),
            )
            for m in memberships
        ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    access: ProjectAccess = Depends(get_project_access),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return a project the current user can enter."""
    with session_factory() as db:
        counts = _member_counts(db, [access.project.id])
    return _to_response(access, member_count=counts.get(access.project.id, 0))


# Members


@router.get("/{project_id}/members", response_model=List[MemberResponse])
def list_members(
    access: ProjectAccess = Depends(get_project_access),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """List the members of a project with their roles."""
    with session_factory() as db:
        memberships = (
            db.execute(
                select(UserRoleProject)
                .join(User)
                .options(
                    selectinload(UserRoleProject.user),
                    selectinload(UserRoleProject.role),
                )
                .where(UserRoleProject.project_id == access.project.id)
                .order_by(User.username)
            )
            .scalars()
            .all()
        )
        return [_member_response(m) for m in memberships]


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    params: MemberAddParams,
    access: ProjectAccess = Depends(require_project_permission("projects.manage")),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Add an active user to the project with a project role."""
    with session_factory() as db:
        role = _project_role(db, params.role_uid)
        if role.uid == OWNER_ROLE_UID:
            _check_can_handle_owners(access)

        user = db.execute(
            select(User).where(User.username == params.username)
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        already = db.get(UserRoleProject, (user.id, access.project.id))
        if already is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That user is already a member of the project",
            )

        membership = UserRoleProject(user=user, project_id=access.project.id, role=role)
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return _member_response(membership)


@router.patch("/{project_id}/members/{user_id}", response_model=MemberResponse)
def change_member_role(
    user_id: int,
    params: MemberRoleParams,
    access: ProjectAccess = Depends(require_project_permission("projects.manage")),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Change the project role of a member."""
    with session_factory() as db:
        membership = _membership(db, access.project.id, user_id)
        role = _project_role(db, params.role_uid)
        if role.id == membership.role_id:
            return _member_response(membership)

        if OWNER_ROLE_UID in (role.uid, membership.role.uid):
            _check_can_handle_owners(access)
        _check_keeps_an_owner(db, membership)

        membership.role = role
        db.commit()
        db.refresh(membership)
        return _member_response(membership)


@router.delete(
    "/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    user_id: int,
    access: ProjectAccess = Depends(get_project_access),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Remove a member from the project.

    Members can always leave a project themselves; removing someone else
    needs ``projects.manage``.
    """
    leaving = user_id == access.user.id
    if not leaving and "projects.manage" not in access.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )

    with session_factory() as db:
        membership = _membership(db, access.project.id, user_id)
        if membership.role.uid == OWNER_ROLE_UID and not leaving:
            _check_can_handle_owners(access)
        _check_keeps_an_owner(db, membership)

        db.delete(membership)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
