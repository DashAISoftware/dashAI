"""Upgrade and downgrade test for dropping the old column fields of sessions."""

import json

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    REVISION as ADD_ROLES,
)
from tests.back.migrations.test_add_column_roles_to_model_session import (
    ROWS,
    _alembic_config,
    _column,
    _seed,
)

REVISION = "9b4e7c2a1f30"
OLD_FIELDS = ("input_columns", "output_columns", "input_column_refs")


def _model_session_columns(engine) -> dict:
    return {c["name"]: c for c in sa.inspect(engine).get_columns("model_session")}


def test_dropping_the_old_fields_keeps_the_roles_and_comes_back(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    before_roles = (
        ScriptDirectory.from_config(cfg).get_revision(ADD_ROLES).down_revision
    )
    command.upgrade(cfg, before_roles)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)
    old = {name: _column(engine, name) for name in OLD_FIELDS}

    command.upgrade(cfg, ADD_ROLES)
    roles = _column(engine, "column_roles")

    command.upgrade(cfg, REVISION)

    columns = _model_session_columns(engine)
    assert not set(OLD_FIELDS) & set(columns)
    assert columns["column_roles"]["nullable"] is False
    assert _column(engine, "column_roles") == roles

    command.downgrade(cfg, ADD_ROLES)

    columns = _model_session_columns(engine)
    assert columns["input_columns"]["nullable"] is False
    assert columns["output_columns"]["nullable"] is False
    assert columns["column_roles"]["nullable"] is True
    assert _column(engine, "input_columns") == old["input_columns"]
    assert _column(engine, "output_columns") == old["output_columns"]
    # A row older than input_column_refs gets the raw refs of its inputs back,
    # which is what the code read it as.
    expected_refs = dict(old["input_column_refs"])
    expected_refs[1] = [{"kind": "raw", "name": name} for name in ROWS[1][0]]
    assert _column(engine, "input_column_refs") == expected_refs

    command.downgrade(cfg, before_roles)
    assert "column_roles" not in _model_session_columns(engine)
    engine.dispose()


def test_a_row_left_without_roles_is_converted_before_the_drop(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, ADD_ROLES)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)  # written after 5d2e8a1c9b47, so column_roles is NULL

    command.upgrade(cfg, REVISION)

    assert _column(engine, "column_roles")[4] == {
        "features": {
            "refs": [
                {"kind": "raw", "name": "hours"},
                {"kind": "raw", "name": "score"},
            ],
            "columns": ["hours", "score"],
        }
    }
    with engine.begin() as conn:
        nulls = conn.execute(
            sa.text("SELECT COUNT(*) FROM model_session WHERE column_roles IS NULL")
        ).scalar_one()
    assert nulls == 0
    assert json.dumps(_column(engine, "column_roles")[1]) == json.dumps(
        {
            "features": {
                "refs": [
                    {"kind": "raw", "name": "SepalLengthCm"},
                    {"kind": "raw", "name": "SepalWidthCm"},
                ],
                "columns": ["SepalLengthCm", "SepalWidthCm"],
            },
            "target": {
                "refs": [{"kind": "raw", "name": "Species"}],
                "columns": ["Species"],
            },
        }
    )
    engine.dispose()
