"""A finished forecasting run, as the rest of the app reads it.

A backtest stores its cuts in ``Run.split_indexes``, in steps, where an x/y
run stores row positions. These pin that the readers of that column which
this PR does not rewrite get nothing from a forecasting run they would
misread: no partition to explain, and a session package that carries the
cuts through untouched (RECONCILING_FORECASTING §2.13).

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

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


def test_explaining_a_backtest_says_it_has_no_partitions_of_rows(client, run_id):
    # Forecasting declares no explainers, but the job is reachable with one
    # named by hand; a backtest's test is measured in steps, not rows.
    from DashAI.back.dependencies.database.models import GlobalExplainer
    from DashAI.back.job.base_job import JobError
    from DashAI.back.job.explainer_job import ExplainerJob

    with client.app.container["session_factory"]() as db:
        explainer = GlobalExplainer(
            name="backtest-explainer",
            run_id=run_id,
            explainer_name="RegressionPermutationFeatureImportance",
            parameters={},
        )
        db.add(explainer)
        db.commit()
        explainer_id = explainer.id

    with pytest.raises(JobError, match="A backtest cuts the series in steps"):
        ExplainerJob(explainer_id=explainer_id, explainer_scope="global").run()


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


def test_a_session_package_carries_the_forecasts_under_the_new_run(
    client, run_id, tmp_path
):
    from DashAI.back.job.report_job import ReportJob

    container = client.app.container
    package = tmp_path / "forecasting.dashai"
    build_session_package(
        _get(client, Run, run_id).model_session_id,
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

    with container["session_factory"]() as db:
        (imported,) = db.query(Run).filter(Run.model_session_id == result["session_id"])
        imported_id = imported.id
    # The original stays, so the import cannot have reused its id.
    assert imported_id != run_id
    response = client.get(f"/api/v1/run/{imported_id}/forecasts")
    assert response.status_code == 200, response.text
    assert response.json() == client.get(f"/api/v1/run/{run_id}/forecasts").json()

    report = client.post(
        "/api/v1/report/",
        json={
            "run_id": imported_id,
            "report_name": "ForecastVsActual",
            "parameters": {},
        },
    )
    ReportJob(report_id=report.json()["id"]).run()
    artifacts = client.get(f"/api/v1/report/{report.json()['id']}/artifacts")
    assert artifacts.status_code == 200, artifacts.text


def test_training_a_run_again_replaces_its_metrics(client, tmp_path):
    """A run trained again without a reset, as ``/jobs`` does, keeps one set.

    A summary row twice would make ``get_metrics_for_run`` keep whichever came
    last, and a fold row twice would pair the wrong origins in the paired
    tests that read ``/fold-metrics`` by position.
    """
    from DashAI.back.job.model_job import ModelJob

    session_id = _session(client, tmp_path, _monthly())
    other = _train(client, session_id, "NaiveForecaster")

    def rows():
        with client.app.container["session_factory"]() as db:
            return sorted(
                (m.split.name, m.level.name, m.name, m.fold_index)
                for m in db.query(Metric).filter(Metric.run_id == other)
            )

    first = rows()
    ModelJob(run_id=other).run()

    assert rows() == first
    folds = client.get(f"/api/v1/run/{other}/fold-metrics").json()
    assert {name: len(values) for name, values in folds.items()} == {
        "MAE": 3,
        "RMSE": 3,
    }


@pytest.mark.parametrize("broken", ["forecast", "score"])
def test_a_trial_that_scores_no_number_stops_the_search_and_says_where(
    client, tmp_path, monkeypatch, broken
):
    """A trial with no number to compare is neither skipped nor averaged.

    A NaN forecast makes sklearn's MAE raise ``ValueError``, and a NaN score
    makes Optuna mark the trial failed; either way, with every trial like it,
    the run ended in "every trial failed, narrow the ranges", which names no
    metric and no window and gives the wrong advice.
    """
    import numpy as np

    from DashAI.back.job.base_job import JobError
    from DashAI.back.job.model_job import ModelJob
    from DashAI.back.metrics.regression.mae import MAE
    from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster
    from tests.back.api.test_forecasting_acceptance import _create_run

    if broken == "forecast":
        monkeypatch.setattr(
            SeasonalNaiveForecaster,
            "_forecast",
            lambda self, h, x=None: np.full(h, np.nan),
        )
    else:
        monkeypatch.setattr(
            MAE, "score_forecast", classmethod(lambda cls, forecast: float("nan"))
        )
    session_id = _session(client, tmp_path, _monthly())
    searched = {
        "season_length": {
            "optimize": True,
            "fixed_value": 12,
            "lower_bound": 2,
            "upper_bound": 12,
        }
    }
    other = _create_run(
        client,
        session_id,
        "SeasonalNaiveForecaster",
        searched,
        goal_metric="MAE",
        optimizer="OptunaOptimizer",
    )

    # Names the metric and the window, in whichever order.
    with pytest.raises(JobError, match=r"(?=.*\bMAE\b)(?=.*validation window)"):
        ModelJob(run_id=other).run()


def test_an_undefined_goal_metric_names_the_window_and_the_dates(client, tmp_path):
    from DashAI.back.job.base_job import JobError
    from DashAI.back.job.model_job import ModelJob
    from tests.back.api.test_forecasting_acceptance import _create_run

    # Step 40 is 2023-05-01, in the validation window that starts at step 39.
    session_id = _session(
        client, tmp_path, _monthly(zero_at=40), metrics=["MAE", "MAPE"]
    )
    searched = {
        "season_length": {
            "optimize": True,
            "fixed_value": 12,
            "lower_bound": 2,
            "upper_bound": 12,
        }
    }
    other = _create_run(
        client,
        session_id,
        "SeasonalNaiveForecaster",
        searched,
        goal_metric="MAPE",
        optimizer="OptunaOptimizer",
    )

    with pytest.raises(JobError) as raised:
        ModelJob(run_id=other).run()

    message = str(raised.value)
    assert "the validation window from 2023-04-01 to 2023-06-01" in message
    assert "the actual value is zero on 2023-05-01." in message
    assert message.endswith("Choose another optimization metric.")


def test_a_backtest_reads_the_preprocessing_fitted_for_each_cut(
    client, tmp_path, monkeypatch
):
    """A session that preprocesses its exogenous variables trains.

    Until the exogenous role (RECONCILING_FORECASTING §7) forecasting took no
    session preprocessing, and a run of a session that carried fitted
    artifacts anyway failed with "takes no session preprocessing". Each cut
    now reads its exogenous columns through the fit made for it.
    """
    import numpy as np

    from DashAI.back.core.enums.status import RunStatus
    from DashAI.back.job.model_job import ModelJob
    from DashAI.back.units.apply_cut_preprocessing_unit import (
        ApplyCutPreprocessingUnit,
    )
    from tests.back.api.test_forecasting_acceptance import (
        CV,
        ROLLING,
        _create_run,
        _session_body,
        _upload,
    )

    frame = _monthly().assign(promo=np.arange(48, dtype=float))
    body = _session_body(
        _upload(client, frame, tmp_path, "fitted-preprocessing"),
        strategy=CV,
        splits=ROLLING,
        preprocessing=[
            {
                "converter": "StandardScaler",
                "params": {},
                "scope": [{"kind": "raw", "name": "promo"}],
            }
        ],
    )
    body["column_roles"]["exogenous"] = [{"kind": "raw", "name": "promo"}]
    response = client.post("/api/v1/model-session/", json=body)
    assert response.status_code == 201, response.text
    published = []
    original_execute = ApplyCutPreprocessingUnit.execute

    def recording_execute(self, ctx):
        original_execute(self, ctx)
        published.append(ctx.require("exogenous"))

    monkeypatch.setattr(ApplyCutPreprocessingUnit, "execute", recording_execute)
    run_id = _create_run(client, response.json()["id"], "NaiveForecaster")

    ModelJob(run_id=run_id).run()

    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    (exogenous,) = published
    # Scaled on the steps before each cut, so each cut reads its own values.
    firsts = [cut["values"][0, 0] for cut in exogenous["validation"]]
    assert len(set(firsts)) == len(firsts)


def test_coverage_as_the_goal_metric_fails_the_run(client, tmp_path):
    """Searched for, coverage picks the widest intervals, not a better model.

    The run API refuses this goal (``test_run_goal_metric_api.py``), so the
    run is written straight to the database: the job keeps its own guard for
    runs that do not come through the API.
    """
    from DashAI.back.core.enums.status import RunStatus
    from DashAI.back.job.base_job import JobError
    from DashAI.back.job.model_job import ModelJob

    session_id = _session(client, tmp_path, _monthly())
    searched = {
        "season_length": {
            "optimize": True,
            "fixed_value": 12,
            "lower_bound": 2,
            "upper_bound": 12,
        }
    }
    with client.app.container["session_factory"]() as db:
        run = Run(
            model_session_id=session_id,
            model_name="SeasonalNaiveForecaster",
            name="coverage as the goal",
            parameters=searched,
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={
                "n_trials": 2,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            goal_metric="IntervalCoverage",
            plot_history_path="",
            plot_slice_path="",
            plot_contour_path="",
            plot_importance_path="",
        )
        db.add(run)
        db.commit()
        other = run.id

    with pytest.raises(JobError, match="IntervalCoverage cannot be optimized"):
        ModelJob(run_id=other).run()

    assert _get(client, Run, other).status == RunStatus.ERROR


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


def test_the_forecasts_plot_has_a_figure_per_origin(client, run_id):
    forecasts = client.get(f"/api/v1/run/{run_id}/forecasts").json()

    response = client.get(f"/api/v1/run/{run_id}/forecasts/plot")

    assert response.status_code == 200
    [grouped] = response.json()
    assert grouped["type"] == "grouped"
    assert [g["title"] for g in grouped["groups"]] == [
        "Validation 1",
        "Validation 2",
        "Validation 3",
        "Test",
    ]
    for group, origin in zip(grouped["groups"], forecasts["origins"], strict=True):
        [artifact] = group["artifacts"]
        assert artifact["type"] == "plotly"
        traces = {t["name"]: t for t in json.loads(artifact["payload"])["data"]}
        assert traces["Actual"]["y"] == pytest.approx(origin["actual"])
        assert traces["Forecast"]["y"] == pytest.approx(origin["forecast"])
        assert traces["95% interval"]["y"] == pytest.approx(origin["lower"]["95"])
        assert traces["80% interval"]["y"] == pytest.approx(origin["lower"]["80"])


def test_the_forecasts_plot_speaks_the_requested_language(client, run_id):
    response = client.get(
        f"/api/v1/run/{run_id}/forecasts/plot", headers={"Accept-Language": "es"}
    )

    [grouped] = response.json()
    assert grouped["groups"][-1]["title"] == "Prueba"
    payload = json.loads(grouped["groups"][-1]["artifacts"][0]["payload"])
    assert {t["name"] for t in payload["data"]} >= {"Real", "Pronóstico"}


def test_a_single_origin_is_one_figure_without_a_selector():
    from DashAI.back.evaluation.forecasts_plot import forecasts_artifacts

    origin = {
        "partition": "test",
        "index": 0,
        "dates": ["2023-01-01T00:00:00", "2023-02-01T00:00:00"],
        "actual": [1.0, None],
        "forecast": [1.5, 2.0],
        "lower": {},
        "upper": {},
    }

    [artifact] = forecasts_artifacts({"levels": [], "origins": [origin]})

    assert artifact.type == "plotly"
    names = [t["name"] for t in json.loads(artifact.payload)["data"]]
    assert names == ["Actual", "Forecast"]


def test_a_run_without_forecasts_has_no_forecasts_plot(client, run_id):
    session_id = _get(client, Run, run_id).model_session_id
    pending = _create_run(client, session_id, "NaiveForecaster")

    response = client.get(f"/api/v1/run/{pending}/forecasts/plot")

    assert response.status_code == 404


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


# --- the reports -------------------------------------------------------------


@pytest.mark.parametrize(
    "report_name",
    [
        "ForecastVsActual",
        "ForecastErrorByStep",
        "ResidualsOverTime",
        "ResidualAutocorrelation",
    ],
)
def test_a_report_of_a_forecasting_run_is_drawn_from_its_forecasts(
    client, run_id, report_name
):
    from DashAI.back.job.report_job import ReportJob

    response = client.post(
        "/api/v1/report/",
        json={"run_id": run_id, "report_name": report_name, "parameters": {}},
    )
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]

    ReportJob(report_id=report_id).run()

    artifacts = client.get(f"/api/v1/report/{report_id}/artifacts")
    assert artifacts.status_code == 200, artifacts.text
    assert artifacts.json()[0]["groups"][0]["title"] == "Backtest"


def test_a_forecasting_report_never_loads_the_model(client, tmp_path):
    from DashAI.back.job.report_job import ReportJob

    session_id = _session(client, tmp_path, _monthly())
    other = _train(client, session_id, "NaiveForecaster")
    Path(_get(client, Run, other).run_path).unlink()
    response = client.post(
        "/api/v1/report/",
        json={"run_id": other, "report_name": "ForecastVsActual", "parameters": {}},
    )

    ReportJob(report_id=response.json()["id"]).run()

    artifacts = client.get(f"/api/v1/report/{response.json()['id']}/artifacts")
    assert artifacts.status_code == 200, artifacts.text


def test_a_run_without_its_forecasts_has_no_report(client, tmp_path):
    from DashAI.back.job.base_job import JobError
    from DashAI.back.job.report_job import ReportJob

    session_id = _session(client, tmp_path, _monthly())
    other = _train(client, session_id, "NaiveForecaster")
    forecasts_file(client.app.container["config"]["RUNS_PATH"], str(other)).unlink()
    response = client.post(
        "/api/v1/report/",
        json={"run_id": other, "report_name": "ForecastVsActual", "parameters": {}},
    )

    with pytest.raises(JobError, match="saved no forecasts"):
        ReportJob(report_id=response.json()["id"]).run()


@pytest.fixture(name="exogenous_run")
def a_run_that_read_a_planned_promotion(client, tmp_path):
    import numpy as np

    from DashAI.back.job.model_job import ModelJob
    from tests.back.api.test_forecasting_acceptance import (
        CV,
        ROLLING,
        _create_run,
        _session_body,
        _upload,
    )

    frame = _monthly().assign(promo=[float(i % 4 == 1) for i in range(48)])
    frame["sales"] += 15.0 * frame["promo"] + np.cos(np.arange(48))
    body = _session_body(
        _upload(client, frame, tmp_path, f"exogenous-run-{tmp_path.name}"),
        strategy=CV,
        splits=ROLLING,
    )
    body["column_roles"]["exogenous"] = [{"kind": "raw", "name": "promo"}]
    response = client.post("/api/v1/model-session/", json=body)
    assert response.status_code == 201, response.text
    run_id = _create_run(
        client, response.json()["id"], "ARIMA", {"p": 1, "d": 0, "q": 0}
    )
    ModelJob(run_id=run_id).run()
    return run_id


RECORDED = {
    "used": True,
    "columns": [{"name": "promo", "type": "Float"}],
    "reason": None,
}


def test_the_run_answers_what_it_did_with_the_exogenous(client, exogenous_run):
    response = client.get(f"/api/v1/run/{exogenous_run}")

    assert response.status_code == 200, response.text
    assert response.json()["exogenous"] == RECORDED


def test_a_reset_forgets_what_the_training_recorded(client, exogenous_run):
    assert _get(client, Run, exogenous_run).exogenous == RECORDED

    assert client.patch(f"/api/v1/run/{exogenous_run}/reset").status_code == 200

    assert _get(client, Run, exogenous_run).exogenous is None


def test_a_session_package_carries_what_a_trained_run_recorded(
    client, exogenous_run, tmp_path
):
    container = client.app.container
    package = tmp_path / "exogenous.dashai"
    build_session_package(
        _get(client, Run, exogenous_run).model_session_id,
        [exogenous_run],
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

    with container["session_factory"]() as db:
        (imported,) = db.query(Run).filter(Run.model_session_id == result["session_id"])
        assert imported.exogenous == RECORDED
