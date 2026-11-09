"""The saved plots of a run, the edits made to them, and their lifecycle.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

import pytest

from DashAI.back.dependencies.database.models import Run, RunPlot
from DashAI.back.units.forecast_scope import forecasts_file
from tests.back.api.test_forecasting_acceptance import (
    _create_run,
    _get,
    _monthly,
    _session,
    _train,
)

ORIGINS = ["Validation 1", "Validation 2", "Validation 3", "Test"]
EDIT = {"data": [{"type": "scatter", "y": [1, 2]}], "layout": {"title": "edited"}}


def _rows(client, run_id):
    with client.app.container["session_factory"]() as db:
        return db.query(RunPlot).filter_by(run_id=run_id).all()


def _plots(client, run_id, view="forecasts"):
    return client.get(f"/api/v1/run/{run_id}/plots/{view}")


def _leaves(body):
    [grouped] = body
    return [group["artifacts"][0] for group in grouped["groups"]]


@pytest.fixture(scope="module", name="run_id")
def a_finished_run(client, tmp_path_factory):
    session_id = _session(client, tmp_path_factory.mktemp("run-plots"), _monthly())
    return _train(client, session_id, "SeasonalNaiveForecaster")


@pytest.fixture(name="fresh_run")
def a_run_to_change(client, tmp_path):
    return _train(client, _session(client, tmp_path, _monthly()), "NaiveForecaster")


def test_get_returns_one_figure_per_origin(client, run_id):
    response = _plots(client, run_id)

    assert response.status_code == 200
    [grouped] = response.json()
    assert grouped["type"] == "grouped"
    assert [group["title"] for group in grouped["groups"]] == ORIGINS
    assert all(leaf["type"] == "plotly" for leaf in _leaves(response.json()))


def test_an_edit_survives_a_read_and_only_on_its_origin(client, fresh_run):
    third = _leaves(_plots(client, fresh_run).json())[2]["index"]

    response = client.put(
        f"/api/v1/run/{fresh_run}/plots/forecasts/override",
        json={"index": third, "figure": EDIT},
    )

    assert response.status_code == 200
    leaves = _leaves(_plots(client, fresh_run).json())
    assert leaves[2]["overridden"] is True
    assert json.loads(leaves[2]["payload"]) == EDIT
    assert not leaves[0].get("overridden")


def test_delete_reverts_the_edit(client, fresh_run):
    first = _leaves(_plots(client, fresh_run).json())[0]["index"]
    client.put(
        f"/api/v1/run/{fresh_run}/plots/forecasts/override",
        json={"index": first, "figure": EDIT},
    )

    response = client.delete(
        f"/api/v1/run/{fresh_run}/plots/forecasts/override/{first}"
    )

    assert response.status_code == 200
    assert not _leaves(_plots(client, fresh_run).json())[0].get("overridden")


def test_an_index_that_is_not_a_leaf_is_refused(client, fresh_run):
    response = client.put(
        f"/api/v1/run/{fresh_run}/plots/forecasts/override",
        json={"index": 99, "figure": EDIT},
    )

    assert response.status_code == 422
    assert not any(
        leaf.get("overridden") for leaf in _leaves(_plots(client, fresh_run).json())
    )


def test_an_unknown_view_is_refused(client, run_id):
    assert _plots(client, run_id, "other").status_code == 422


def test_a_view_the_run_does_not_have_is_404(client, run_id):
    response = _plots(client, run_id, "hyperparameter")

    assert response.status_code == 404
    assert "has no hyperparameter plots" in response.text


def test_a_run_that_has_not_finished_has_no_plots(client, run_id):
    session_id = _get(client, Run, run_id).model_session_id
    pending = _create_run(client, session_id, "NaiveForecaster")

    response = _plots(client, pending)

    assert response.status_code == 404
    assert "has not finished" in response.text


def test_an_old_run_gets_its_forecasts_row_on_first_read(client, fresh_run):
    [row] = _rows(client, fresh_run)
    Path(row.artifacts_path).unlink()
    with client.app.container["session_factory"]() as db:
        db.query(RunPlot).filter_by(run_id=fresh_run).delete()
        db.commit()

    response = _plots(client, fresh_run)

    assert response.status_code == 200
    assert [group["title"] for group in response.json()[0]["groups"]] == ORIGINS
    [row] = _rows(client, fresh_run)
    assert row.view == "forecasts"
    assert Path(row.artifacts_path).exists()


def test_backfill_without_the_forecasts_file_is_404(client, fresh_run):
    [row] = _rows(client, fresh_run)
    Path(row.artifacts_path).unlink()
    with client.app.container["session_factory"]() as db:
        db.query(RunPlot).filter_by(run_id=fresh_run).delete()
        db.commit()
    forecasts_file(client.app.container["config"]["RUNS_PATH"], str(fresh_run)).unlink()

    response = _plots(client, fresh_run)

    assert response.status_code == 404
    assert "has no forecasts" in response.text
    assert _rows(client, fresh_run) == []


def test_a_missing_plot_file_is_404(client, fresh_run):
    [row] = _rows(client, fresh_run)
    Path(row.artifacts_path).unlink()

    response = _plots(client, fresh_run)

    assert response.status_code == 404
    assert "has no forecasts plots" in response.text


def test_reset_drops_rows_edits_and_files(client, fresh_run):
    first = _leaves(_plots(client, fresh_run).json())[0]["index"]
    client.put(
        f"/api/v1/run/{fresh_run}/plots/forecasts/override",
        json={"index": first, "figure": EDIT},
    )
    [row] = _rows(client, fresh_run)

    response = client.patch(f"/api/v1/run/{fresh_run}/reset")

    assert response.status_code == 200
    assert _rows(client, fresh_run) == []
    assert not Path(row.artifacts_path).exists()


def test_deleting_a_run_removes_its_plot_files(client, fresh_run):
    [row] = _rows(client, fresh_run)

    response = client.delete(f"/api/v1/run/{fresh_run}")

    assert response.status_code == 204
    assert _rows(client, fresh_run) == []
    assert not Path(row.artifacts_path).exists()
