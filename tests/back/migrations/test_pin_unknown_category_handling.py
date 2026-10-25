"""Upgrade and downgrade test for pinning how stored encoders treat unknowns.

The one-hot and ordinal encoders now treat a category unseen in fit by
default. A session stored before that keeps the behaviour it was created with:
a step saved without ``handle_unknown`` meant sklearn's "error", and the
migration writes it down so that refitting the session (an import without
artifacts) does not change it.
"""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "c3f1a8d2e6b4"
NOW = datetime(2026, 10, 25, 12, 0, 0)
ROLES = {
    "features": {"refs": [{"kind": "raw", "name": "c"}], "columns": ["c"]},
    "target": {"refs": [{"kind": "raw", "name": "y"}], "columns": ["y"]},
}
SCOPE = [{"kind": "raw", "name": "c"}]


def _steps(*steps):
    return {
        "steps": [
            {"converter": converter, "params": params, "scope": SCOPE}
            for converter, params in steps
        ]
    }


# id -> preprocessing, as stored
ROWS = {
    1: None,
    2: _steps(("OneHotEncoder", {"dtype": "int64"})),
    3: _steps(("OneHotEncoder", {"handle_unknown": "ignore", "dtype": "int64"})),
    4: _steps(("OrdinalEncoder", {}), ("StandardScaler", {})),
    5: _steps(("OrdinalEncoder", {"handle_unknown": "error", "unknown_value": None})),
    6: _steps(("LabelEncoder", {}), ("OneHotEncoder", {})),
    7: {"steps": []},
}


def _seed(engine):
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO dataset (id, name, file_path, status, created, "
                "last_modified) VALUES (1, 'd', '/tmp/d', 'FINISHED', :now, :now)"
            ),
            {"now": NOW},
        )
        for row_id, preprocessing in ROWS.items():
            conn.execute(
                sa.text(
                    "INSERT INTO model_session (id, dataset_id, name, task_name, "
                    "column_roles, train_metrics, validation_metrics, "
                    "test_metrics, evaluation_strategy, splits, preprocessing, "
                    "preprocessing_status, created, last_modified) VALUES "
                    "(:id, 1, :name, 'TabularClassificationTask', :roles, '[]', "
                    "'[]', '[]', 'HoldoutEvaluationStrategy', '{}', "
                    ":preprocessing, 'ready', :now, :now)"
                ),
                {
                    "id": row_id,
                    "name": f"session {row_id}",
                    "roles": json.dumps(ROLES),
                    "preprocessing": (
                        None if preprocessing is None else json.dumps(preprocessing)
                    ),
                    "now": NOW,
                },
            )


def _preprocessing(engine) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            sa.text("SELECT id, preprocessing FROM model_session ORDER BY id")
        ).fetchall()
    return {
        row_id: None if value is None else json.loads(value) for row_id, value in rows
    }


def test_an_encoder_stored_without_handle_unknown_keeps_error(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)

    command.upgrade(cfg, REVISION)

    assert _preprocessing(engine) == {
        1: None,
        2: _steps(("OneHotEncoder", {"dtype": "int64", "handle_unknown": "error"})),
        3: ROWS[3],
        4: _steps(
            ("OrdinalEncoder", {"handle_unknown": "error"}), ("StandardScaler", {})
        ),
        5: ROWS[5],
        6: _steps(("LabelEncoder", {}), ("OneHotEncoder", {"handle_unknown": "error"})),
        7: ROWS[7],
    }

    # Writing down what the old code did changes nothing for it, so the
    # downgrade leaves the rows as they are.
    upgraded = _preprocessing(engine)
    command.downgrade(cfg, down_revision)
    assert _preprocessing(engine) == upgraded
    engine.dispose()
