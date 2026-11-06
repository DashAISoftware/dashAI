"""Upgrade and downgrade test for the column roles of model sessions."""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

REVISION = "5d2e8a1c9b47"
NOW = datetime(2026, 10, 22, 12, 0, 0)

BINARIZED_REFS = [
    {"kind": "raw", "name": "SepalWidthCm"},
    {"kind": "group", "step": 0, "slot": None, "name": None},
]

# id -> (input_columns, output_columns, input_column_refs, preprocessing_status)
ROWS = {
    # No preprocessing, as every session the wizard creates without steps.
    1: (["SepalLengthCm", "SepalWidthCm"], ["Species"], None, "ready"),
    # Preprocessing fitted: input_columns already holds the resolved names.
    2: (
        ["SepalWidthCm", "bin_SepalLengthCm"],
        ["Species"],
        BINARIZED_REFS,
        "ready",
    ),
    # Preprocessing not fitted yet: input_columns holds the raw placeholders.
    3: (["SepalWidthCm"], ["Species"], BINARIZED_REFS, "pending"),
    # Clustering: no target.
    4: (
        ["hours", "score"],
        [],
        [{"kind": "raw", "name": "hours"}, {"kind": "raw", "name": "score"}],
        "ready",
    ),
    # Written by the POST without preprocessing: raw refs, one per input.
    5: (["text"], ["label"], [{"kind": "raw", "name": "text"}], "ready"),
}


def _alembic_config(db_path) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _seed(engine: sa.Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO dataset (id, name, file_path, status, created, "
                "last_modified) VALUES (1, 'iris', '/tmp/iris', 'FINISHED', "
                ":now, :now)"
            ),
            {"now": NOW},
        )
        for row_id, (inputs, outputs, refs, status) in ROWS.items():
            conn.execute(
                sa.text(
                    "INSERT INTO model_session (id, dataset_id, name, task_name, "
                    "input_columns, output_columns, train_metrics, "
                    "validation_metrics, test_metrics, evaluation_strategy, "
                    "splits, preprocessing, input_column_refs, "
                    "preprocessing_status, created, last_modified) VALUES "
                    "(:id, 1, :name, 'TabularClassificationTask', :inputs, "
                    ":outputs, '[]', '[]', '[]', 'HoldoutEvaluationStrategy', "
                    "'{}', NULL, :refs, :status, :now, :now)"
                ),
                {
                    "id": row_id,
                    "name": f"session {row_id}",
                    "inputs": json.dumps(inputs),
                    "outputs": json.dumps(outputs),
                    "refs": None if refs is None else json.dumps(refs),
                    "status": status,
                    "now": NOW,
                },
            )


def _column(engine: sa.Engine, name: str) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            sa.text(f"SELECT id, {name} FROM model_session ORDER BY id")
        ).fetchall()
    return {
        row_id: None if value is None else json.loads(value) for row_id, value in rows
    }


def test_column_roles_migration_round_trip(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)
    before = {
        name: _column(engine, name)
        for name in ("input_columns", "output_columns", "input_column_refs")
    }

    command.upgrade(cfg, REVISION)

    assert _column(engine, "column_roles") == {
        1: {
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
        },
        2: {
            "features": {
                "refs": BINARIZED_REFS,
                "columns": ["SepalWidthCm", "bin_SepalLengthCm"],
            },
            "target": {
                "refs": [{"kind": "raw", "name": "Species"}],
                "columns": ["Species"],
            },
        },
        3: {
            "features": {"refs": BINARIZED_REFS, "columns": ["SepalWidthCm"]},
            "target": {
                "refs": [{"kind": "raw", "name": "Species"}],
                "columns": ["Species"],
            },
        },
        4: {
            "features": {
                "refs": [
                    {"kind": "raw", "name": "hours"},
                    {"kind": "raw", "name": "score"},
                ],
                "columns": ["hours", "score"],
            },
        },
        5: {
            "features": {
                "refs": [{"kind": "raw", "name": "text"}],
                "columns": ["text"],
            },
            "target": {
                "refs": [{"kind": "raw", "name": "label"}],
                "columns": ["label"],
            },
        },
    }
    # The old fields are left as they were: a later revision drops them.
    for name, values in before.items():
        assert _column(engine, name) == values, name

    command.downgrade(cfg, down_revision)

    columns = {c["name"] for c in sa.inspect(engine).get_columns("model_session")}
    assert "column_roles" not in columns
    for name, values in before.items():
        assert _column(engine, name) == values, name
    engine.dispose()
