"""Upgrade and downgrade test for what a run's empty parameters resolved to."""

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "c7e2a9d4f1b8"


def _run_columns(engine) -> dict:
    return {c["name"]: c for c in sa.inspect(engine).get_columns("run")}


def test_the_column_comes_nullable_and_goes(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, REVISION)
    engine = sa.create_engine(f"sqlite:///{db_path}")

    assert _run_columns(engine)["resolved_parameters"]["nullable"] is True

    command.downgrade(cfg, down_revision)
    assert "resolved_parameters" not in _run_columns(engine)
    engine.dispose()
