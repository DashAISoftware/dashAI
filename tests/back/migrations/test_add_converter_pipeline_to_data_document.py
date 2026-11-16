"""Upgrade and downgrade test for the document converter pipeline column."""

import json

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "c9e2f4a7b1d3"
PIPELINE = [{"converter": "TextSplitter", "params": {"split_by": "Sentences"}}]


def _columns(engine):
    return {c["name"]: c for c in sa.inspect(engine).get_columns("data_document")}


def _seed(engine):
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO data_document (id, name, file_name, file_type, "
                "file_path, status, created, last_modified) VALUES (1, 'doc', "
                "'notes.txt', 'txt', '', 'FINISHED', '2026-11-09 00:00:00', "
                "'2026-11-09 00:00:00')"
            )
        )


def test_converter_pipeline_round_trip(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)
    assert "converter_pipeline" not in _columns(engine)

    command.upgrade(cfg, REVISION)

    assert _columns(engine)["converter_pipeline"]["nullable"] is True
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE data_document SET converter_pipeline = :pipeline WHERE id = 1"
            ),
            {"pipeline": json.dumps(PIPELINE)},
        )
    with engine.connect() as connection:
        raw = connection.execute(
            sa.text("SELECT converter_pipeline FROM data_document WHERE id = 1")
        ).scalar()
    assert json.loads(raw) == PIPELINE

    command.downgrade(cfg, down_revision)

    assert "converter_pipeline" not in _columns(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT name FROM data_document WHERE id = 1")
            ).scalar()
            == "doc"
        )
    engine.dispose()
