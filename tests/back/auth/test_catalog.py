import logging

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from DashAI.back.auth.catalog import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    PROJECT_PERMISSIONS,
    ROLES,
    sync_auth_catalog,
)
from DashAI.back.dependencies.database.models import Base, Permission, Role


@pytest.fixture
def session_factory():
    # StaticPool keeps one connection, so every session sees the same
    # in-memory database
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


def _role_permissions(session_factory, uid):
    with session_factory() as db:
        role = db.execute(select(Role).where(Role.uid == uid)).scalar_one()
        return {p.uid for p in role.permissions}


def test_creates_every_permission_and_role(session_factory):
    sync_auth_catalog(session_factory)

    with session_factory() as db:
        permissions = set(db.execute(select(Permission.uid)).scalars())
        roles = {
            r.uid: (r.scope, r.is_system) for r in db.execute(select(Role)).scalars()
        }

    assert permissions == set(ALL_PERMISSIONS)
    assert roles == {
        "admin": ("global", True),
        "member": ("global", False),
        "owner": ("project", True),
        "manager": ("project", False),
        "collaborator": ("project", False),
        "reader": ("project", True),
    }


def test_fixed_roles_follow_their_rule(session_factory):
    sync_auth_catalog(session_factory)

    assert _role_permissions(session_factory, "admin") == set(ALL_PERMISSIONS)
    assert _role_permissions(session_factory, "owner") == set(PROJECT_PERMISSIONS)
    assert _role_permissions(session_factory, "reader") == {
        uid for uid in PROJECT_PERMISSIONS if uid.endswith(".read")
    }


def test_collaborator_cannot_delete_export_or_manage(session_factory):
    sync_auth_catalog(session_factory)

    permissions = _role_permissions(session_factory, "collaborator")

    assert "documents.index" in permissions
    assert "generative.execute" in permissions
    assert "projects.manage" not in permissions
    assert not any(uid.endswith((".delete", ".export")) for uid in permissions)


def test_permission_names_are_unique():
    # The permission table has a unique name, so a repeated label would make
    # the startup sync fail
    names = [spec.name for spec in PERMISSIONS]

    assert len(names) == len(set(names))


def test_editable_roles_start_with_their_defaults(session_factory):
    sync_auth_catalog(session_factory)

    for spec in ROLES:
        if not spec.fixed:
            assert _role_permissions(session_factory, spec.uid) == set(
                spec.permissions()
            )


def test_second_run_changes_nothing(session_factory, caplog):
    sync_auth_catalog(session_factory)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="DashAI.back.auth.catalog"):
        sync_auth_catalog(session_factory)

    with session_factory() as db:
        assert len(db.execute(select(Role)).scalars().all()) == len(ROLES)
        assert len(db.execute(select(Permission)).scalars().all()) == len(
            ALL_PERMISSIONS
        )
    # Nothing was created or updated, so nothing is reported
    assert "Auth catalog synced" not in caplog.text


def test_fixed_role_edits_are_reverted(session_factory):
    sync_auth_catalog(session_factory)
    with session_factory() as db:
        admin = db.execute(select(Role).where(Role.uid == "admin")).scalar_one()
        admin.permissions = []
        db.commit()

    sync_auth_catalog(session_factory)

    assert _role_permissions(session_factory, "admin") == set(ALL_PERMISSIONS)


def test_editable_role_edits_are_kept(session_factory):
    sync_auth_catalog(session_factory)
    with session_factory() as db:
        member = db.execute(select(Role).where(Role.uid == "member")).scalar_one()
        extra = db.execute(
            select(Permission).where(Permission.uid == "datasets.write")
        ).scalar_one()
        member.permissions.append(extra)
        db.commit()

    sync_auth_catalog(session_factory)

    assert _role_permissions(session_factory, "member") == {
        "datasets.read",
        "datasets.write",
        "models.read",
    }


def test_unknown_permission_is_kept_and_reported(session_factory, caplog):
    sync_auth_catalog(session_factory)
    with session_factory() as db:
        db.add(Permission(uid="legacy.permission", name="Legacy"))
        db.commit()

    with caplog.at_level(logging.WARNING, logger="DashAI.back.auth.catalog"):
        sync_auth_catalog(session_factory)

    with session_factory() as db:
        kept = db.execute(
            select(Permission).where(Permission.uid == "legacy.permission")
        ).scalar_one_or_none()
    assert kept is not None
    assert "legacy.permission" in caplog.text
