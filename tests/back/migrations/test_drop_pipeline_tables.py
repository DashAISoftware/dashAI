"""Upgrade and downgrade test for the removal of the pipeline tables."""

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "b1e5c3a7d9f2"
PIPELINE_TABLES = {
    "pipeline",
    "pipeline_run",
    "pipeline_node_run",
    "pipeline_node_artifact",
}


def _tables(engine) -> set:
    return set(sa.inspect(engine).get_table_names())


def test_the_pipeline_tables_go_and_come_back(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    assert PIPELINE_TABLES <= _tables(engine)
    before = _tables(engine)

    command.upgrade(cfg, REVISION)
    assert before - _tables(engine) == PIPELINE_TABLES

    command.downgrade(cfg, down_revision)
    assert _tables(engine) == before
    engine.dispose()


def test_the_orm_no_longer_declares_pipeline_tables():
    from DashAI.back.dependencies.database import models

    declared = set(models.Base.metadata.tables)
    assert not declared & PIPELINE_TABLES
