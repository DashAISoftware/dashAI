"""Upgrade and downgrade test for the workflow of generative sessions."""

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

REVISION = "a7f3c9e2d5b8"
NOW = datetime(2026, 11, 10, 12, 0, 0)

TEXT = "TextToTextGenerationTask"
IMAGE = "TextToImageGenerationTask"

SESSIONS = {
    1: (TEXT, "Qwen25_05BInstruct", json.dumps({"temperature": 0.7})),
    2: (
        "RAGTask",
        "RAGPipeline",
        json.dumps(
            {
                "generation_model": {"component": "Llama32_1BInstruct", "params": {}},
                "documents": [1],
            }
        ),
    ),
    3: ("RAGTask", "RAGPipeline", "{not json"),
    4: ("RAGTask", "RAGPipeline", json.dumps({"documents": []})),
    5: (IMAGE, "StableDiffusionV2", json.dumps({})),
    6: (
        "RAGTask",
        "RAGPipeline",
        json.dumps({"generation_model": {"component": "", "params": {}}}),
    ),
}

HISTORY = {
    11: (2, "RAGPipeline", {"generation_model": {"component": "Llama32_3BInstruct"}}),
    12: (2, "RAGPipeline", {"generation_model": {"component": "Llama32_1BInstruct"}}),
    13: (4, "RAGPipeline", {"documents": []}),
    14: (2, None, {"generation_model": {"component": "Llama32_1BInstruct"}}),
    15: (1, "Qwen25_05BInstruct", {"temperature": 0.7}),
    16: (3, "RAGPipeline", "{not json"),
}


def _alembic_config(db_path) -> Config:
    """Point alembic at a scratch database.

    Parameters
    ----------
    db_path : Path
        SQLite file to migrate.

    Returns
    -------
    Config
        Alembic configuration.
    """
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def _seed(engine: sa.Engine) -> None:
    """Insert the sessions and history rows of the scenario.

    Parameters
    ----------
    engine : sa.Engine
        Engine on the database at the previous revision.
    """
    with engine.begin() as conn:
        for session_id, (task, model, parameters) in SESSIONS.items():
            conn.execute(
                sa.text(
                    "INSERT INTO generative_session (id, created, last_modified, "
                    "task_name, model_name, parameters, name) VALUES "
                    "(:id, :now, :now, :task, :model, :parameters, :name)"
                ),
                {
                    "id": session_id,
                    "now": NOW,
                    "task": task,
                    "model": model,
                    "parameters": parameters,
                    "name": f"session {session_id}",
                },
            )
        for history_id, (session_id, model, parameters) in HISTORY.items():
            conn.execute(
                sa.text(
                    "INSERT INTO parameter_history (id, session_id, parameters, "
                    "modified_at, model_name) VALUES "
                    "(:id, :session_id, :parameters, :now, :model)"
                ),
                {
                    "id": history_id,
                    "session_id": session_id,
                    "parameters": (
                        parameters
                        if isinstance(parameters, str)
                        else json.dumps(parameters)
                    ),
                    "now": NOW,
                    "model": model,
                },
            )


def _values(engine: sa.Engine, table: str, column: str) -> dict:
    """Read one column of a table keyed by id.

    Parameters
    ----------
    engine : sa.Engine
        Engine on the database.
    table : str
        Table name.
    column : str
        Column name.

    Returns
    -------
    dict
        ``{id: value}``.
    """
    with engine.begin() as conn:
        rows = conn.execute(
            sa.text(f"SELECT id, {column} FROM {table} ORDER BY id")
        ).fetchall()
    return dict(rows)


def test_generative_sessions_get_workflows_round_trip(tmp_path):
    """RAG rows become RAGWorkflow sessions and come back on downgrade."""
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    _seed(engine)

    command.upgrade(cfg, REVISION)

    assert _values(engine, "generative_session", "workflow_name") == {
        1: "InferenceWorkflow",
        2: "RAGWorkflow",
        3: "RAGWorkflow",
        4: "RAGWorkflow",
        5: "InferenceWorkflow",
        6: "RAGWorkflow",
    }
    assert _values(engine, "generative_session", "task_name") == {
        1: TEXT,
        2: TEXT,
        3: TEXT,
        4: TEXT,
        5: IMAGE,
        6: TEXT,
    }
    assert _values(engine, "generative_session", "model_name") == {
        1: "Qwen25_05BInstruct",
        2: "Llama32_1BInstruct",
        3: "RAGPipeline",
        4: "RAGPipeline",
        5: "StableDiffusionV2",
        6: "RAGPipeline",
    }
    assert _values(engine, "parameter_history", "model_name") == {
        11: "Llama32_3BInstruct",
        12: "Llama32_1BInstruct",
        13: "RAGPipeline",
        14: None,
        15: "Qwen25_05BInstruct",
        16: "RAGPipeline",
    }
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO generative_session (id, created, last_modified, "
                "task_name, model_name, parameters, name) VALUES "
                "(7, :now, :now, :task, 'Qwen25_05BInstruct', '{}', 'new')"
            ),
            {"now": NOW, "task": TEXT},
        )
    assert _values(engine, "generative_session", "workflow_name")[7] == (
        "InferenceWorkflow"
    )
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM generative_session WHERE id = 7"))

    command.downgrade(cfg, down_revision)

    columns = {c["name"] for c in sa.inspect(engine).get_columns("generative_session")}
    assert "workflow_name" not in columns
    assert _values(engine, "generative_session", "task_name") == {
        session_id: task for session_id, (task, _model, _p) in SESSIONS.items()
    }
    assert _values(engine, "generative_session", "model_name") == {
        session_id: model for session_id, (_task, model, _p) in SESSIONS.items()
    }
    assert _values(engine, "parameter_history", "model_name") == {
        11: "RAGPipeline",
        12: "RAGPipeline",
        13: "RAGPipeline",
        14: None,
        15: "Qwen25_05BInstruct",
        16: "RAGPipeline",
    }
    engine.dispose()
