"""Upgrade test for moving the HPO plot columns of a run into run_plot rows."""

import pickle
from datetime import datetime

import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory

from tests.back.migrations.test_add_column_roles_to_model_session import (
    _alembic_config,
)

REVISION = "b8e4f1a6c3d2"
NOW = datetime(2026, 11, 9, 12, 0, 0)
FIGURE = '{"data": [], "layout": {}}'
TYPED = {"type": "plotly", "payload": FIGURE, "title": "slice", "index": 0}


def _filler(column) -> object:
    kind = column["type"].__class__.__name__.upper()
    if "INT" in kind:
        return 1
    if "DATE" in kind:
        return NOW
    if "JSON" in kind:
        return "{}"
    return "x"


def _insert_run(engine, run_id: int, plots: dict) -> None:
    columns = sa.inspect(engine).get_columns("run")
    values = {
        column["name"]: _filler(column)
        for column in columns
        if not column["nullable"] and column["default"] is None
    }
    values.update({"id": run_id, "status": "FINISHED", **plots})
    names = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    with engine.begin() as conn:
        conn.execute(sa.text(f"INSERT INTO run ({names}) VALUES ({params})"), values)


def test_hpo_pickles_become_one_row_and_the_columns_go(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")

    history = tmp_path / "history_objective_plot_1.pickle"
    history.write_bytes(pickle.dumps(FIGURE))
    slice_ = tmp_path / "slice_plot_1.pickle"
    slice_.write_bytes(pickle.dumps(TYPED))
    _insert_run(
        engine,
        1,
        {
            "plot_history_path": str(history),
            "plot_slice_path": str(slice_),
            "plot_importance_path": str(tmp_path / "gone.pickle"),
        },
    )
    _insert_run(engine, 2, {"plot_history_path": str(tmp_path / "also_gone.pickle")})

    command.upgrade(cfg, REVISION)

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT run_id, view, artifacts_path FROM run_plot")
        ).all()
    assert [(run_id, view) for run_id, view, _ in rows] == [(1, "hyperparameter")]
    with open(rows[0][2], "rb") as file:
        leaves = pickle.load(file)
    assert [leaf["type"] for leaf in leaves] == ["plotly", "plotly"]
    assert leaves[0]["payload"] == FIGURE
    assert not history.exists()
    assert not slice_.exists()
    columns = {column["name"] for column in sa.inspect(engine).get_columns("run")}
    assert "plot_history_path" not in columns
    assert "plot_importance_path" not in columns
    engine.dispose()


def test_the_downgrade_brings_the_columns_back_empty(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, REVISION)

    command.downgrade(cfg, down_revision)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    columns = {column["name"] for column in sa.inspect(engine).get_columns("run")}
    assert {
        "plot_history_path",
        "plot_slice_path",
        "plot_contour_path",
        "plot_importance_path",
    } <= columns
    engine.dispose()


def _migration():
    import importlib.util
    from pathlib import Path

    path = next(Path("DashAI/alembic/versions").glob(f"{REVISION}_*.py"))
    spec = importlib.util.spec_from_file_location("move_hpo_plots", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_unreadable_pickle_is_skipped_not_fatal(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    history = tmp_path / "history_objective_plot_1.pickle"
    history.write_bytes(pickle.dumps(FIGURE))
    truncated = tmp_path / "slice_plot_1.pickle"
    truncated.write_bytes(b"")
    _insert_run(
        engine,
        1,
        {"plot_history_path": str(history), "plot_slice_path": str(truncated)},
    )
    empty = tmp_path / "history_objective_plot_2.pickle"
    empty.write_bytes(b"")
    _insert_run(engine, 2, {"plot_history_path": str(empty)})

    command.upgrade(cfg, REVISION)

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT run_id, artifacts_path FROM run_plot")
        ).all()
    assert [run_id for run_id, _ in rows] == [1]
    with open(rows[0][1], "rb") as file:
        assert len(pickle.load(file)) == 1
    engine.dispose()


def test_moving_the_plots_leaves_the_old_pickles_for_after_the_drop(tmp_path):
    db_path = tmp_path / "test.db"
    cfg = _alembic_config(db_path)
    down_revision = (
        ScriptDirectory.from_config(cfg).get_revision(REVISION).down_revision
    )
    command.upgrade(cfg, down_revision)
    engine = sa.create_engine(f"sqlite:///{db_path}")
    history = tmp_path / "history_objective_plot_1.pickle"
    history.write_bytes(pickle.dumps(FIGURE))
    _insert_run(engine, 1, {"plot_history_path": str(history)})

    with engine.begin() as conn:
        moved = _migration().move_legacy_plots(conn)

    assert history.exists()
    assert moved == [str(history)]
    engine.dispose()
