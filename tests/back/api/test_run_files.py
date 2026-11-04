"""The files of a run go with it, on every path that deletes or resets runs.

A run leaves files in ``RUNS_PATH``: its model, the four plots of its search
and, for a backtest, its forecasts. Their names come from the run's id, and
SQLite hands a deleted id to the next run, so a file left behind is read as
the next run's own. Every path that deletes runs -- the run, the reset, a
session, sessions in bulk, a dataset, datasets in bulk -- removes all of them,
and only once the delete has committed: a delete that fails keeps its files
(RECONCILING_FORECASTING §5.8).

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import ModelSession, Run
from DashAI.back.units.forecast_scope import forecasts_file
from tests.back.api.test_forecasting_acceptance import _get, _monthly, _session, _train

PLOT_FIELDS = (
    "plot_history_path",
    "plot_slice_path",
    "plot_contour_path",
    "plot_importance_path",
)


def _trained_run(client, session_id) -> int:
    """A finished backtest run, with a file standing in for each plot."""
    run_id = _train(client, session_id, "NaiveForecaster")
    runs_path = Path(client.app.container["config"]["RUNS_PATH"])
    with client.app.container["session_factory"]() as db:
        run = db.get(Run, run_id)
        for field in PLOT_FIELDS:
            plot = runs_path / f"{field}_{run_id}.pickle"
            plot.write_bytes(b"plot")
            setattr(run, field, str(plot))
        db.commit()
    return run_id


def _files(client, run_id) -> list:
    run = _get(client, Run, run_id)
    runs_path = client.app.container["config"]["RUNS_PATH"]
    return [
        Path(run.run_path),
        *(Path(getattr(run, field)) for field in PLOT_FIELDS),
        forecasts_file(runs_path, str(run_id)),
    ]


def _left(files) -> list:
    return [str(path) for path in files if path.exists()]


def _dataset_of(client, session_id) -> int:
    return _get(client, ModelSession, session_id).dataset_id


def test_deleting_a_run_removes_its_files(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    run_id = _trained_run(client, session_id)
    files = _files(client, run_id)
    assert _left(files) == [str(path) for path in files]

    assert client.delete(f"/api/v1/run/{run_id}").status_code == 204

    assert _left(files) == []


def test_resetting_a_run_removes_its_files(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    run_id = _trained_run(client, session_id)
    files = _files(client, run_id)

    assert client.patch(f"/api/v1/run/{run_id}/reset").status_code == 200

    assert _left(files) == []


def test_deleting_a_session_removes_the_files_of_its_runs(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    files = _files(client, _trained_run(client, session_id))

    assert client.delete(f"/api/v1/model-session/{session_id}").status_code == 204

    assert _left(files) == []


def test_deleting_sessions_in_bulk_removes_the_files_of_their_runs(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    files = _files(client, _trained_run(client, session_id))

    response = client.request(
        "DELETE", "/api/v1/model-session/", json={"ids": [session_id]}
    )

    assert response.status_code == 204, response.text
    assert _left(files) == []


def test_deleting_a_dataset_removes_the_files_of_its_runs(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    files = _files(client, _trained_run(client, session_id))

    response = client.delete(f"/api/v1/dataset/{_dataset_of(client, session_id)}")

    assert response.status_code == 204, response.text
    assert _left(files) == []


def test_deleting_datasets_in_bulk_removes_the_files_of_their_runs(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    files = _files(client, _trained_run(client, session_id))

    response = client.request(
        "DELETE", "/api/v1/dataset/", json={"ids": [_dataset_of(client, session_id)]}
    )

    assert response.status_code == 204, response.text
    assert _left(files) == []


@pytest.fixture(name="failing_run_commit")
def a_commit_that_fails_on_a_run(monkeypatch):
    """Fail the commit of any transaction that deletes or changes a run.

    Only that one: the reset clears the run's metrics in a transaction of its
    own, which has to go through for the reset to reach its commit.
    """
    commit = Session.commit

    def failing(self):
        if any(isinstance(row, Run) for row in (*self.deleted, *self.dirty)):
            raise SQLAlchemyError("database is locked")
        return commit(self)

    monkeypatch.setattr(Session, "commit", failing)


@pytest.mark.parametrize("action", ["delete", "reset"])
def test_a_failed_commit_keeps_the_files(client, tmp_path, request, action):
    session_id = _session(client, tmp_path, _monthly())
    run_id = _trained_run(client, session_id)
    files = _files(client, run_id)
    request.getfixturevalue("failing_run_commit")

    if action == "delete":
        response = client.delete(f"/api/v1/run/{run_id}")
    else:
        response = client.patch(f"/api/v1/run/{run_id}/reset")

    assert response.status_code == 500, response.text
    assert _left(files) == [str(path) for path in files]
