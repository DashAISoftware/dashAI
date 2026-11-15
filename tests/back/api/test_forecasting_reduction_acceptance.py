"""Acceptance cases for the reduction model, written before it exists.

Each case states what the PR has to deliver, from the design in
RECONCILING_FORECASTING §2.15 and the plan in §8.2. Each is a strict ``xfail``
until the slice that delivers it, made to fail for the reason it names before
the fix (an ``ImportError`` or a 422 for an unregistered model does not
count), and its marker comes off with the fix.

Where the regressor does not matter, the cases use ``LinearRegression``, the
lightest one; ``RandomForestRegression`` only where the case is about a
regressor with hyperparameters of its own (§8.2).

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

from pathlib import Path

import numpy as np
import pytest

from DashAI.back.core.enums.status import PredictionStatus, RunStatus
from DashAI.back.dependencies.database.models import Prediction, Run
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.test_forecasting_acceptance import (
    CV,
    HOLDOUT,
    HOLDOUT_STRATEGY,
    ROLLING,
    _create_run,
    _get,
    _monthly,
    _session,
)

MODEL = "RecursiveRegressionForecaster"
LINEAR = {"regressor": {"component": "LinearRegression", "params": {}}}


def pending(slice_name: str):
    return pytest.mark.xfail(strict=True, reason=f"PR 6, slice {slice_name}")


def _train(client, session_id, params=None, **run) -> int:
    run_id = _create_run(client, session_id, MODEL, params or LINEAR, **run)
    ModelJob(run_id=run_id).run()
    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    return run_id


def _kept(client, run_id):
    from DashAI.back.models.forecasting.recursive_regression import (
        RecursiveRegressionForecaster,
    )

    return RecursiveRegressionForecaster.load(_get(client, Run, run_id).run_path)


# --------------------------------------------------------------------------- #
# Slice 2: the dependency
# --------------------------------------------------------------------------- #


def test_skforecast_is_installed_at_its_pinned_version():
    from importlib.metadata import version

    assert version("skforecast") == "0.26.0"


# --------------------------------------------------------------------------- #
# Slice 3: trials without intervals
# --------------------------------------------------------------------------- #


@pending("3")
def test_a_search_trial_asks_a_model_with_intervals_for_none(monkeypatch):
    from DashAI.back.metrics.regression.mae import MAE
    from DashAI.back.models.forecasting.naive import NaiveForecaster
    from DashAI.back.units import backtest_forecaster_unit
    from tests.back.api.test_forecasting_models_net import _trial_score

    asked = []
    original = backtest_forecaster_unit.forecast_origin

    def recording(*args, **kwargs):
        # forecast_origin(model, series, origin, horizon, grid, partition,
        # index, levels, x=...)
        asked.append(list(args[7]))
        return original(*args, **kwargs)

    monkeypatch.setattr(backtest_forecaster_unit, "forecast_origin", recording)

    assert NaiveForecaster.SUPPORTS_INTERVALS
    _trial_score(NaiveForecaster(), "monthly", "rolling", MAE)

    # Only the goal metric is scored, and no optimizable metric reads bounds.
    assert asked == [[], [], []]


# --------------------------------------------------------------------------- #
# Slice 4: the scikit-learn estimator inside a DashAI regressor
# --------------------------------------------------------------------------- #


@pending("4")
@pytest.mark.parametrize(
    "name",
    [
        "AdaBoostRegression",
        "BayesianRidgeRegression",
        "DecisionTreeRegression",
        "ElasticNetRegression",
        "ExtraTreesRegression",
        "GradientBoostingR",
        "HistGradientBoostingRegression",
        "KNeighborsRegression",
        "LassoRegression",
        "LinearRegression",
        "LinearSVR",
        "RandomForestRegression",
        "RidgeRegression",
        "SVR",
    ],
)
def test_the_extracted_estimator_keeps_every_hyperparameter(client, name):
    from sklearn.base import clone

    from DashAI.back.models.forecasting.recursive_regression import (
        sklearn_estimator,
    )
    from tests.back.api.test_forecasting_models_net import _regressor

    registry = client.app.container["component_registry"]
    regressor = _regressor(registry, name)

    estimator = sklearn_estimator(regressor)

    expected = {key: getattr(regressor, key) for key in estimator.get_params()}
    assert expected  # a scikit-learn estimator always has some
    assert clone(estimator).get_params() == expected
    assert type(estimator).__module__.startswith("sklearn.")


# --------------------------------------------------------------------------- #
# Slice 6: registered, end to end
# --------------------------------------------------------------------------- #


@pending("6")
def test_the_model_offers_the_scikit_learn_regressors(client):
    registry = client.app.container["component_registry"]
    field = registry[MODEL]["schema"]["properties"]["regressor"]

    response = client.get(
        "/api/v1/component/",
        params={"select_types": ["Model"], "component_parent": field["parent"]},
    )

    assert response.status_code == 200, response.text
    names = {component["name"] for component in response.json()}
    assert len(names) == 14
    assert "LinearRegression" in names
    assert "MLPRegression" not in names
    assert "SVC" not in names
    assert field["placeholder"]["component"] == "LinearRegression"


@pending("6")
@pytest.mark.parametrize(
    ("strategy", "splits"), [(HOLDOUT_STRATEGY, HOLDOUT), (CV, ROLLING)]
)
def test_a_run_backtests_with_nested_intervals_and_their_coverage(
    client, tmp_path, strategy, splits
):
    session_id = _session(
        client,
        tmp_path,
        _monthly(),
        strategy=strategy,
        splits=splits,
        metrics=["MAE", "IntervalCoverage"],
    )

    run_id = _train(client, session_id)

    origins = client.get(f"/api/v1/run/{run_id}/forecasts").json()["origins"]
    for origin in origins:
        lower, upper = origin["lower"], origin["upper"]
        assert all(a <= b for a, b in zip(lower["95"], lower["80"], strict=True))
        assert all(a >= b for a, b in zip(upper["95"], upper["80"], strict=True))
    coverage = client.get(f"/api/v1/run/{run_id}").json()["validation_metrics"]
    assert 0.0 <= coverage["IntervalCoverage"] <= 1.0


@pending("6")
def test_left_out_the_season_sets_twelve_lags_on_a_monthly_series(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())

    model = _kept(client, _train(client, session_id))

    assert model.season_length == 12
    assert model.resolved_lags() == 12


@pending("6")
def test_a_search_over_the_nested_regressor_keeps_its_best_value(client, tmp_path):
    session_id = _session(client, tmp_path, _monthly())
    searched = {
        "regressor": {
            "component": "RandomForestRegression",
            "params": {
                # One value, so the search runs and still lands on a known
                # best: Optuna takes no seed.
                "n_estimators": {
                    "optimize": True,
                    "fixed_value": 5,
                    "lower_bound": 7,
                    "upper_bound": 7,
                },
                "random_state": 0,
            },
        }
    }

    run_id = _train(
        client,
        session_id,
        searched,
        goal_metric="MAE",
        optimizer="OptunaOptimizer",
    )

    model = _kept(client, run_id)
    assert model.regressor.n_estimators == 7
    assert model.fitted_estimator().n_estimators == 7


@pending("6")
def test_with_exogenous_columns_the_run_reads_them_and_forecasts_the_future(
    client, tmp_path
):
    from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
    from tests.back.api.test_forecasting_exogenous_acceptance import (
        PROMO,
        _future,
        _upload,
    )
    from tests.back.api.test_forecasting_exogenous_acceptance import (
        _session as _exogenous_session,
    )

    session_id = _exogenous_session(client, tmp_path, exogenous=PROMO)
    run_id = _train(client, session_id)
    assert _get(client, Run, run_id).exogenous["used"] is True

    future = _future()
    dataset_id = _upload(client, future, tmp_path, "future")
    response = client.post(
        "/api/v1/predict/", json={"run_id": run_id, "dataset_id": dataset_id}
    )
    assert response.status_code == 200, response.text
    PredictJob(prediction_id=response.json()["id"]).run()

    prediction = _get(client, Prediction, response.json()["id"])
    assert prediction.status == PredictionStatus.FINISHED
    saved = load_dataset(str(Path(prediction.results_path) / "dataset")).to_pandas()
    assert len(saved) == len(future)


@pending("6")
@pytest.mark.parametrize("nested", ["MLPRegression", "SVC"])
def test_a_regressor_that_is_not_scikit_learn_fails_the_run_when_built(
    client, tmp_path, nested
):
    from DashAI.back.job.base_job import JobError

    session_id = _session(client, tmp_path, _monthly())
    run_id = _create_run(
        client, session_id, MODEL, {"regressor": {"component": nested, "params": {}}}
    )

    with pytest.raises(JobError, match="scikit-learn regressor"):
        ModelJob(run_id=run_id).run()

    assert _get(client, Run, run_id).status == RunStatus.ERROR


@pending("6")
def test_a_series_too_short_for_the_lags_fails_naming_them(client, tmp_path):
    from DashAI.back.job.base_job import JobError

    session_id = _session(
        client, tmp_path, _monthly(24), strategy=HOLDOUT_STRATEGY, splits=HOLDOUT
    )
    run_id = _create_run(
        client, session_id, MODEL, {**LINEAR, "lags": 20, "differentiation": 1}
    )

    with pytest.raises(JobError, match=r"20 lags.*differentiation 1"):
        ModelJob(run_id=run_id).run()


@pending("6")
def test_the_kept_model_predicts_by_horizon(client, tmp_path):
    from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

    session_id = _session(client, tmp_path, _monthly())
    run_id = _train(client, session_id)

    response = client.post("/api/v1/predict/", json={"run_id": run_id, "horizon": 5})
    assert response.status_code == 200, response.text
    PredictJob(prediction_id=response.json()["id"]).run()

    prediction = _get(client, Prediction, response.json()["id"])
    assert prediction.status == PredictionStatus.FINISHED
    saved = load_dataset(str(Path(prediction.results_path) / "dataset"))
    assert len(saved) == 5
    assert np.isfinite(_kept(client, run_id).predict(5).point).all()
