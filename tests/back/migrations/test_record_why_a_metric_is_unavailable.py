"""Upgrade and downgrade test for recording why a metric is unavailable."""

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "b8e3d1f4a6c2"


def _metric_columns(engine) -> dict:
    return {c["name"]: c for c in sa.inspect(engine).get_columns("metric")}


def _insert_metric(connection, value, reason=None) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO metric (run_id, split, level, name, value, "
            "unavailable_reason, step, timestamp) VALUES (1, 'TEST', 'LAST', "
            "'MAPE', :value, :reason, 0, '2026-10-26 00:00:00')"
        ),
        {"value": value, "reason": reason},
    )


def test_a_value_can_be_null_with_a_reason_and_back(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, REVISION)
    engine = sa.create_engine(f"sqlite:///{db_path}")

    columns = _metric_columns(engine)
    assert columns["value"]["nullable"] is True
    assert columns["unavailable_reason"]["nullable"] is True

    with engine.begin() as connection:
        connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
        _insert_metric(connection, 12.5)
        _insert_metric(connection, None, "MAPE divides by each actual value")

    command.downgrade(cfg, down_revision)

    columns = _metric_columns(engine)
    assert "unavailable_reason" not in columns
    assert columns["value"]["nullable"] is False
    with engine.connect() as connection:
        values = connection.execute(sa.text("SELECT value FROM metric")).scalars()
        # The unavailable row has no place in the old schema; the scored one
        # survives the downgrade.
        assert list(values) == [12.5]
    engine.dispose()
