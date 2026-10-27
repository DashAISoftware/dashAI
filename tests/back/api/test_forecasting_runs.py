"""A finished forecasting run, as the rest of the app reads it.

A backtest stores its cuts in ``Run.split_indexes``, in steps, where an x/y
run stores row positions. These pin that the readers of that column which
this PR does not rewrite get nothing from a forecasting run they would
misread: no partition to explain, and a session package that carries the
cuts through untouched (RECONCILING_FORECASTING §2.13).

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json

import pandas as pd
import pytest

from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.session_package.export import build_session_package
from DashAI.back.session_package.load import import_session_package
from DashAI.back.units.forecast_scope import forecasts_file
from tests.back.api.test_forecasting_acceptance import (
    _create_run,
    _get,
    _monthly,
    _session,
    _train,
)

CUTS = {
    "horizon": 3,
    "validation_origins": [36, 39, 42],
    "test_origin": 45,
    "n_steps": 48,
}


@pytest.fixture(scope="module", name="run_id")
def a_finished_rolling_origin_run(client, tmp_path_factory):
    session_id = _session(
        client, tmp_path_factory.mktemp("forecasting-runs"), _monthly()
    )
    return _train(client, session_id, "SeasonalNaiveForecaster")


def test_the_run_stores_its_cuts_and_the_parameters_it_used(client, run_id):
    run = _get(client, Run, run_id)

    assert json.loads(run.split_indexes) == CUTS
    # The season left out of the parameters came from the monthly grid.
    assert run.parameters == {"season_length": 12}


def test_the_run_has_no_partition_to_explain(client, run_id):
    response = client.get(f"/api/v1/explainer/explainable-splits/{run_id}")

    assert response.status_code == 200, response.text
    assert response.json() == {"splits": []}


def test_a_session_package_carries_the_cuts_and_the_metrics(client, run_id, tmp_path):
    container = client.app.container
    run = _get(client, Run, run_id)
    package = tmp_path / "forecasting.dashai"
    build_session_package(
        run.model_session_id,
        [run_id],
        True,
        package,
        container["session_factory"],
        container["component_registry"],
    )

    result = import_session_package(
        package,
        container["session_factory"],
        container["component_registry"],
        container["config"],
        container["job_queue"],
    )

    def metric_rows(db, of_run):
        return sorted(
            (
                (m.split.name, m.level.name, m.name, m.fold_index, m.value)
                for m in db.query(Metric).filter(Metric.run_id == of_run)
            ),
            key=lambda row: [str(field) for field in row],
        )

    with container["session_factory"]() as db:
        (imported,) = db.query(Run).filter(Run.model_session_id == result["session_id"])
        assert json.loads(imported.split_indexes) == CUTS
        assert metric_rows(db, imported.id) == metric_rows(db, run_id)
        folds = [row for row in metric_rows(db, run_id) if row[1] == "FOLD"]
        assert len(folds) == 2 * 3  # MAE and RMSE on three origins


# --- the forecasts file ------------------------------------------------------


def test_the_forecasts_are_what_refitting_on_each_cut_gives(client, run_id):
    from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

    frame = _monthly()
    series = frame["sales"].to_numpy(dtype=float)
    dates = list(pd.to_datetime(frame["date"]))

    body = client.get(f"/api/v1/run/{run_id}/forecasts").json()

    assert (body["freq"], body["horizon"], body["levels"]) == ("MS", 3, [80, 95])
    origins = [*CUTS["validation_origins"], CUTS["test_origin"]]
    assert [o["origin_step"] for o in body["origins"]] == origins
    for record, origin in zip(body["origins"], origins, strict=True):
        model = SeasonalNaiveForecaster(season_length=12).fit(series[:origin])
        expected = model.predict(3, levels=[80, 95])
        window = slice(origin, origin + 3)
        assert record["dates"] == [d.isoformat() for d in dates[window]]
        assert record["actual"] == pytest.approx(list(series[window]))
        assert record["forecast"] == pytest.approx(list(expected.point))
        for level in (80, 95):
            assert record["lower"][str(level)] == pytest.approx(
                list(expected.lower[level])
            )
            assert record["upper"][str(level)] == pytest.approx(
                list(expected.upper[level])
            )


def test_a_run_that_has_not_finished_has_no_forecasts(client, run_id):
    session_id = _get(client, Run, run_id).model_session_id
    pending = _create_run(client, session_id, "NaiveForecaster")

    response = client.get(f"/api/v1/run/{pending}/forecasts")

    assert response.status_code == 404
    assert "has not finished" in response.text


def test_a_finished_run_without_its_file_has_no_forecasts(client, run_id, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    other = _train(client, session_id, "NaiveForecaster")
    forecasts_file(client.app.container["config"]["RUNS_PATH"], str(other)).unlink()

    response = client.get(f"/api/v1/run/{other}/forecasts")

    assert response.status_code == 404
    assert "has no forecasts" in response.text


def test_the_file_goes_with_the_run(client, tmp_path):
    def path_of(run):
        return forecasts_file(client.app.container["config"]["RUNS_PATH"], str(run))

    session_id = _session(client, tmp_path, _monthly())
    deleted = _train(client, session_id, "NaiveForecaster")
    reset = _train(client, session_id, "NaiveForecaster")
    assert path_of(deleted).exists()
    assert path_of(reset).exists()

    assert client.delete(f"/api/v1/run/{deleted}").status_code == 204
    assert client.patch(f"/api/v1/run/{reset}/reset").status_code == 200

    assert not path_of(deleted).exists()
    assert not path_of(reset).exists()
