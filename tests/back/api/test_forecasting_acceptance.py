"""Acceptance cases for the forecasting core, written before the rewrite.

Each case states what the rewrite has to deliver, from FORECASTING Â§7 and the
decisions in RECONCILING_FORECASTING Â§2.13. Every one is a strict ``xfail``
until the slice that delivers it, so a case that starts passing early fails
the suite and its marker has to come off.

Before a slice fixes a case, the case is made to fail for the reason it names:
an ``ImportError`` or a 422 for an unregistered task does not count.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.metrics import LevelEnum
from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.dependencies.database.models import Dataset, Metric, Run
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob

TASK = "SingleSeriesForecastingTask"


def pending(reason: str):
    return pytest.mark.xfail(strict=True, reason=reason)


# --------------------------------------------------------------------------- #
# Series and datasets
# --------------------------------------------------------------------------- #


def _monthly(n: int = 48, zero_at=None) -> pd.DataFrame:
    steps = np.arange(n)
    values = 100.0 + 0.8 * steps + 10.0 * np.sin(2 * np.pi * steps / 12)
    if zero_at is not None:
        values[zero_at] = 0.0
    dates = pd.date_range("2020-01-01", periods=n, freq="MS")
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": values})


def _dataset(frame: pd.DataFrame):
    schema = {
        "date": {"type": "Date", "dtype": "%Y-%m-%d"},
        "sales": {"type": "Float", "dtype": "float64"},
    }
    return transform_dataset_with_schema(to_dashai_dataset(frame), schema)


def _get(client: TestClient, model, row_id):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        row = db.get(model, row_id)
        db.expunge(row)
        return row


def _upload(client: TestClient, frame: pd.DataFrame, directory: Path, name: str):
    path = directory / f"{name}.csv"
    frame.to_csv(path, index=False)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        entry = Dataset(name=name, file_path="")
        db.add(entry)
        db.commit()
        db.refresh(entry)
        DatasetJob(
            job_type="DatasetJob",
            kwargs={
                "dataset_id": entry.id,
                "url": "",
                "params": {
                    "name": name,
                    "dataloader": "CSVDataLoader",
                    "separator": ",",
                    "inferred_types": {
                        column: (
                            {"type": "Date", "dtype": "%Y-%m-%d"}
                            if column == "date"
                            else {"type": "Float", "dtype": "float64"}
                        )
                        for column in frame.columns
                    },
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _session_body(dataset_id: int, *, strategy: str, splits: dict, **extra) -> dict:
    metrics = extra.pop("metrics", ["MAE", "RMSE"])
    return {
        "dataset_id": dataset_id,
        "task_name": TASK,
        "name": f"acceptance-{dataset_id}-{strategy}",
        "column_roles": {
            "time_index": [{"kind": "raw", "name": "date"}],
            "series": [{"kind": "raw", "name": "sales"}],
        },
        "train_metrics": [],
        "validation_metrics": metrics,
        "test_metrics": metrics,
        "evaluation_strategy": strategy,
        "splits": json.dumps(splits),
        "preprocessing": extra.pop("preprocessing", []),
    }


ROLLING = {"splitter_name": "RollingOriginSplitter", "horizon": 3, "n_origins": 3}
HOLDOUT = {"splitter_name": "TemporalHoldoutSplitter", "horizon": 3}
CV = "ForecastingCrossValidationEvaluationStrategy"
HOLDOUT_STRATEGY = "ForecastingHoldoutEvaluationStrategy"


def _create_run(client, session_id, model, params=None, goal_metric="", optimizer=""):
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session_id,
            "model_name": model,
            "name": f"{model} acceptance",
            "parameters": params or {},
            "optimizer_name": optimizer,
            "optimizer_parameters": (
                {"n_trials": 2, "sampler": "TPESampler", "pruner": "None"}
                if optimizer
                else {}
            ),
            "plot_history_path": "",
            "plot_slice_path": "",
            "plot_contour_path": "",
            "plot_importance_path": "",
            "goal_metric": goal_metric,
            "description": "",
            "nested": None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _train(client, session_id: int, model: str, params=None, goal_metric=""):
    run_id = _create_run(client, session_id, model, params, goal_metric)
    ModelJob(run_id=run_id).run()
    return run_id


def _session(client, tmp_path, frame, *, strategy=CV, splits=ROLLING, **extra):
    dataset_id = _upload(client, frame, tmp_path, f"acc-{tmp_path.name}")
    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=strategy, splits=splits, **extra),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --------------------------------------------------------------------------- #
# Slice 3: the grid
# --------------------------------------------------------------------------- #


def _broken(case: str) -> pd.DataFrame:
    frame = _monthly(24)
    if case == "gap":
        return frame.drop(index=[5, 6]).reset_index(drop=True)
    if case == "duplicate":
        return pd.concat([frame, frame.iloc[[4]]]).reset_index(drop=True)
    if case == "empty_date":
        frame.loc[7, "date"] = None
        return frame
    if case == "no_frequency":
        frame["date"] = [
            (pd.Timestamp("2020-01-01") + pd.Timedelta(days=int(d))).strftime(
                "%Y-%m-%d"
            )
            for d in np.cumsum(np.random.RandomState(3).randint(1, 40, size=24))
        ]
        return frame
    if case == "empty_value":
        frame.loc[9, "sales"] = np.nan
        return frame
    raise AssertionError(case)


@pytest.mark.parametrize(
    "case", ["gap", "duplicate", "empty_date", "no_frequency", "empty_value"]
)
def test_a_series_off_its_grid_is_refused_with_a_message(case):
    from DashAI.back.tasks.time_grid import validate_grid

    frame = _broken(case)
    dates = pd.to_datetime(frame["date"])
    with pytest.raises(ValueError, match="TimeResampler"):
        validate_grid(dates, frame["sales"].astype(float))


# --------------------------------------------------------------------------- #
# Slice 4: the model contract
# --------------------------------------------------------------------------- #


def _models():
    from DashAI.back.models.forecasting.arima import ARIMA
    from DashAI.back.models.forecasting.exponential_smoothing import (
        ExponentialSmoothing,
    )
    from DashAI.back.models.forecasting.naive import NaiveForecaster
    from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

    return [NaiveForecaster, SeasonalNaiveForecaster, ARIMA, ExponentialSmoothing]


@pytest.mark.parametrize("index", range(4))
def test_a_model_forecasts_steps_from_values_alone(index):
    model = _models()[index]()
    model.fit(np.asarray(_monthly()["sales"]))

    forecast = model.predict(5)

    assert len(forecast.point) == 5
    with pytest.raises(TypeError):
        model.predict(_dataset(_monthly(3)).select_columns(["date"]))


def test_arima_forecasts_a_seasonal_series_with_its_seasonal_part():
    from DashAI.back.models.forecasting.arima import ARIMA

    season = [10.0, 20.0, 15.0, 30.0, 25.0, 5.0, 12.0, 18.0, 22.0, 28.0, 8.0, 16.0]
    model = ARIMA(
        p=0, d=0, q=0, seasonal_p=0, seasonal_d=1, seasonal_q=0, season_length=12
    )
    model.fit(np.asarray(season * 4))

    assert model.predict(12).point == pytest.approx(season, abs=1e-6)


@pytest.mark.parametrize("name", ["ARIMA", "ExponentialSmoothing"])
def test_a_model_gives_nested_prediction_intervals(name):
    model = {cls.__name__: cls for cls in _models()}[name]()
    model.fit(np.asarray(_monthly()["sales"]))

    forecast = model.predict(4, levels=[80, 95])

    for level in (80, 95):
        assert (forecast.lower[level] < forecast.point).all()
        assert (forecast.point < forecast.upper[level]).all()
    assert (forecast.lower[95] < forecast.lower[80]).all()


# --------------------------------------------------------------------------- #
# Slice 5: the registry
# --------------------------------------------------------------------------- #


def test_nothing_registered_names_the_forecasting_family(client):
    registry = client.app.container["component_registry"]

    assert TASK in registry
    assert "ForecastingTask" not in registry
    for component in registry.get_components_by_types(select=None):
        compatible = getattr(component["class"], "COMPATIBLE_COMPONENTS", [])
        assert "ForecastingTask" not in compatible, component["name"]


# --------------------------------------------------------------------------- #
# Slice 6a: MAPE and zeros
# --------------------------------------------------------------------------- #


def test_mape_refuses_a_zero_actual_with_a_reason():
    from DashAI.back.metrics.forecasting.mape import MAPE
    from DashAI.back.metrics.undefined_metric import UndefinedMetricError

    with pytest.raises(UndefinedMetricError, match="zero"):
        MAPE.score(np.array([0.0, 10.0]), np.array([1.0, 11.0]))


# --------------------------------------------------------------------------- #
# Slice 6b: the cuts, in steps
# --------------------------------------------------------------------------- #


def test_a_series_too_short_for_its_cuts_is_refused(client, tmp_path):
    dataset_id = _upload(client, _monthly(8), tmp_path, "acc-short")
    body = _session_body(dataset_id, strategy=CV, splits=ROLLING)

    response = client.post("/api/v1/model-session/", json=body)

    assert response.status_code == 422
    assert "horizon" in response.text


def test_a_forecasting_session_with_preprocessing_is_refused(client, tmp_path):
    # The step scales a column outside every role, so neither an unregistered
    # task nor a protected role is what refuses it: only the rule that a
    # forecasting session takes no preprocessing yet.
    frame = _monthly().assign(promo=np.arange(48, dtype=float))
    dataset_id = _upload(client, frame, tmp_path, "acc-preprocessing")
    step = {
        "converter": "StandardScaler",
        "params": {},
        "scope": [{"kind": "raw", "name": "promo"}],
    }
    body = _session_body(dataset_id, strategy=CV, splits=ROLLING, preprocessing=[step])

    response = client.post("/api/v1/model-session/", json=body)

    assert response.status_code == 422
    assert "takes no preprocessing" in response.text


# --------------------------------------------------------------------------- #
# Slice 6c: the backtest
# --------------------------------------------------------------------------- #


def test_rolling_origin_scores_every_origin_over_the_horizon(client, tmp_path):
    shuffled = _monthly().sample(frac=1.0, random_state=0).reset_index(drop=True)
    session_id = _session(client, tmp_path, shuffled)

    run_id = _train(client, session_id, "NaiveForecaster")

    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    cuts = json.loads(_get(client, Run, run_id).split_indexes)
    assert cuts == {
        "horizon": 3,
        "validation_origins": [36, 39, 42],
        "test_origin": 45,
        "n_steps": 48,
    }
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        folds = (
            db.query(Metric)
            .filter(Metric.run_id == run_id, Metric.level == LevelEnum.FOLD)
            .all()
        )
    assert sorted({row.fold_index for row in folds}) == [0, 1, 2]


def test_holdout_scores_validation_and_test_over_the_same_horizon(client, tmp_path):
    session_id = _session(
        client, tmp_path, _monthly(), strategy=HOLDOUT_STRATEGY, splits=HOLDOUT
    )

    run_id = _train(client, session_id, "NaiveForecaster")

    cuts = json.loads(_get(client, Run, run_id).split_indexes)
    assert cuts["validation_origins"] == [42]
    assert cuts["test_origin"] == 45


def test_the_season_length_defaults_to_twelve_on_a_monthly_series(client, tmp_path):
    from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

    session_id = _session(client, tmp_path, _monthly())

    run_id = _train(client, session_id, "SeasonalNaiveForecaster")

    model = SeasonalNaiveForecaster.load(_get(client, Run, run_id).run_path)
    assert model.season_length == 12


def test_the_kept_model_has_seen_the_whole_series(client, tmp_path):
    from DashAI.back.models.forecasting.naive import NaiveForecaster

    frame = _monthly()
    session_id = _session(client, tmp_path, frame)

    run_id = _train(client, session_id, "NaiveForecaster")

    model = NaiveForecaster.load(_get(client, Run, run_id).run_path)
    assert model.predict(1).point[0] == pytest.approx(frame["sales"].iloc[-1])


def test_mape_on_a_series_with_a_zero_is_unavailable(client, tmp_path):
    session_id = _session(
        client, tmp_path, _monthly(zero_at=40), metrics=["MAE", "MAPE"]
    )

    run_id = _train(client, session_id, "NaiveForecaster")

    run = client.get(f"/api/v1/run/{run_id}").json()
    assert "MAPE" not in run["validation_metrics"]
    assert "zero" in run["validation_metrics_unavailable"]["MAPE"]


def test_mape_as_the_goal_metric_on_a_zero_fails_the_run(client, tmp_path):
    from DashAI.back.job.base_job import JobError

    session_id = _session(
        client, tmp_path, _monthly(zero_at=40), metrics=["MAE", "MAPE"]
    )
    # A search, so the goal metric is what the trials are measured by.
    searched = {
        "season_length": {
            "optimize": True,
            "fixed_value": 12,
            "lower_bound": 2,
            "upper_bound": 12,
        }
    }
    run_id = _create_run(
        client,
        session_id,
        "SeasonalNaiveForecaster",
        searched,
        goal_metric="MAPE",
        optimizer="OptunaOptimizer",
    )

    with pytest.raises(JobError, match="optimization metric MAPE has no value"):
        ModelJob(run_id=run_id).run()

    assert _get(client, Run, run_id).status == RunStatus.ERROR


# --------------------------------------------------------------------------- #
# Slice 6d: the forecasts file
# --------------------------------------------------------------------------- #


def test_the_forecasts_of_every_origin_can_be_read(client, tmp_path):
    frame = _monthly()
    session_id = _session(client, tmp_path, frame)
    run_id = _train(client, session_id, "NaiveForecaster")

    response = client.get(f"/api/v1/run/{run_id}/forecasts")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [o["partition"] for o in body["origins"]] == [
        "validation",
        "validation",
        "validation",
        "test",
    ]
    test = body["origins"][-1]
    assert test["dates"] == [
        pd.Timestamp(date).isoformat() for date in frame["date"].iloc[45:]
    ]
    assert test["actual"] == pytest.approx(list(frame["sales"].iloc[45:]))
    assert test["forecast"] == pytest.approx([frame["sales"].iloc[44]] * 3)


# --------------------------------------------------------------------------- #
# Slice 7: prediction by horizon
# --------------------------------------------------------------------------- #


def test_the_task_declares_it_predicts_by_horizon(client):
    registry = client.app.container["component_registry"]

    assert registry[TASK]["metadata"]["prediction_mode"] == "horizon"
    assert registry["RegressionTask"]["metadata"]["prediction_mode"] == "rows"


def test_no_partition_of_a_forecasting_run_is_predictable(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    run_id = _train(client, session_id, "NaiveForecaster")

    response = client.get(f"/api/v1/predict/splits/{run_id}")

    assert response.status_code == 200
    assert response.json()["splits"] == []


# --------------------------------------------------------------------------- #
# Slice 8: reports
# --------------------------------------------------------------------------- #


@pending("slice 8: reports draw the saved forecasts against their dates")
def test_the_forecast_report_draws_against_dates(client, tmp_path):
    from DashAI.back.reports.forecasting.forecast_vs_actual import ForecastVsActual

    frame = _monthly()
    session_id = _session(client, tmp_path, frame)
    run_id = _train(client, session_id, "NaiveForecaster")
    forecasts = client.get(f"/api/v1/run/{run_id}/forecasts").json()

    artifacts = ForecastVsActual().compute_forecasts(forecasts)

    figure = json.loads(artifacts[0].payload)
    assert figure["data"][0]["x"][0] == frame["date"].iloc[36]
