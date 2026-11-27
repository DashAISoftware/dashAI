import logging
import os
import stat

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from DashAI.back.auth.catalog import sync_auth_catalog
from DashAI.back.auth.passwords import hash_password, verify_password
from DashAI.back.auth.system_account import (
    PASSWORD_ENV_VAR,
    ensure_system_account,
    forget_initial_password,
)
from DashAI.back.dependencies.database.models import Base, Role, User


@pytest.fixture
def session_factory():
    # StaticPool keeps one connection, so every session sees the same
    # in-memory database
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sync_auth_catalog(factory)
    yield factory
    engine.dispose()


@pytest.fixture
def config(tmp_path):
    return {
        "ADMIN_USERNAME": "admin",
        "ADMIN_EMAIL": "Admin@DashAI.local",
        "ADMIN_PASSWORD_PATH": tmp_path / "initial_admin_password",
    }


@pytest.fixture(autouse=True)
def _no_password_from_the_environment(monkeypatch):
    monkeypatch.delenv(PASSWORD_ENV_VAR, raising=False)


def _system_accounts(session_factory):
    with session_factory() as db:
        return [
            (user.username, user.email, user.global_role.uid, user.password_hash)
            for user in db.execute(select(User).where(User.is_system)).scalars()
        ]


def _add_member(session_factory, username, email):
    with session_factory() as db:
        member = db.execute(select(Role).where(Role.uid == "member")).scalar_one()
        db.add(
            User(
                username=username,
                email=email,
                password_hash=hash_password("secret-pass-123"),
                social_name="Someone",
                global_role_id=member.id,
            )
        )
        db.commit()


def test_creates_an_admin_with_a_generated_password(session_factory, config):
    ensure_system_account(session_factory, config)

    [(username, email, role, password_hash)] = _system_accounts(session_factory)
    password = config["ADMIN_PASSWORD_PATH"].read_text(encoding="utf-8").strip()
    assert (username, email, role) == ("admin", "admin@dashai.local", "admin")
    assert len(password) >= 20
    assert verify_password(password, password_hash)


@pytest.mark.skipif(os.name == "nt", reason="Windows has no POSIX permissions")
def test_only_the_owner_can_read_the_password_file(session_factory, config):
    ensure_system_account(session_factory, config)

    mode = stat.S_IMODE(config["ADMIN_PASSWORD_PATH"].stat().st_mode)
    assert mode == stat.S_IRUSR | stat.S_IWUSR


def test_uses_the_password_from_the_environment(session_factory, config, monkeypatch):
    monkeypatch.setenv(PASSWORD_ENV_VAR, "chosen-pass-123")

    ensure_system_account(session_factory, config)

    [(_, _, _, password_hash)] = _system_accounts(session_factory)
    assert verify_password("chosen-pass-123", password_hash)
    assert not config["ADMIN_PASSWORD_PATH"].exists()


def test_later_starts_change_nothing(session_factory, config, monkeypatch):
    ensure_system_account(session_factory, config)
    before = _system_accounts(session_factory)
    password_file = config["ADMIN_PASSWORD_PATH"].read_text(encoding="utf-8")

    # Neither a new password nor new names reach an account that exists
    monkeypatch.setenv(PASSWORD_ENV_VAR, "chosen-pass-123")
    config["ADMIN_USERNAME"] = "root"
    ensure_system_account(session_factory, config)

    assert _system_accounts(session_factory) == before
    assert config["ADMIN_PASSWORD_PATH"].read_text(encoding="utf-8") == password_file


@pytest.mark.parametrize(
    ("username", "email"),
    [("admin", "someone@example.com"), ("someone", "admin@dashai.local")],
)
def test_never_takes_over_an_existing_account(
    session_factory, config, caplog, username, email
):
    _add_member(session_factory, username, email)

    with caplog.at_level(logging.ERROR):
        ensure_system_account(session_factory, config)

    assert _system_accounts(session_factory) == []
    assert not config["ADMIN_PASSWORD_PATH"].exists()
    assert "was not created" in caplog.text


def test_forget_initial_password_deletes_the_file(session_factory, config):
    ensure_system_account(session_factory, config)

    forget_initial_password(config)
    forget_initial_password(config)

    assert not config["ADMIN_PASSWORD_PATH"].exists()
