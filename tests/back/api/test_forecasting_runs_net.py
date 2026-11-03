"""Regression net for the forecasting runs a session without exogenous makes.

Written before the exogenous PR (RECONCILING_FORECASTING §7) and recorded on
its base, develop ``182120b0a``, with ``DASHAI_RECORD_FORECASTING_RUNS_NET=1``.
That PR rewires the backtest: a unit between preparing the series and
building the model, ``x`` through ``forecast_origin``, the final fit and the
horizon prediction. A session with no exogenous role must come out of all of
it exactly as before, and this is what pins it, through the API and the jobs
the way the app runs them:

- the forecasts file of every origin, with its dates and intervals;
- the metric rows, the cuts and the parameters the run kept;
- the horizon prediction, saved and as ``/predict/splits`` declares it.

``test_forecasting_core_net.py`` pins the four models on their own; this pins
the runs around them. ARIMA's and ETS's numbers are compared to the
tolerances that net gives them, for the same reasons (platform BLAS, and the
``ETSModel`` fit); everything else to a relative 1e-9.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

import pytest

from DashAI.back.core.enums.status import PredictionStatus, RunStatus
from DashAI.back.dependencies.database.models import Metric, Prediction, Run
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.golden_net import Golden
from tests.back.api.test_column_roles_net import _saved_dataset
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

GOLDEN = Golden(
    Path(__file__).with_name("forecasting_runs_net_golden.json"),
    "DASHAI_RECORD_FORECASTING_RUNS_NET",
)

#: Searched over one value, so the search runs its trials and still lands on
#: a known best: Optuna takes no seed.
ONE_VALUE_SEARCH = {
    "p": {"optimize": True, "fixed_value": 1, "lower_bound": 1, "upper_bound": 1}
}

#: name: (model, parameters, searched, relative tolerance)
RUNS = {
    "naive": ("NaiveForecaster", {}, False, 1e-9),
    "seasonal_naive": ("SeasonalNaiveForecaster", {}, False, 1e-9),
    "arima_110": ("ARIMA", {"p": 1, "d": 1, "q": 0}, False, 1e-6),
    "arima_searched": ("ARIMA", {**ONE_VALUE_SEARCH, "d": 1, "q": 0}, True, 1e-6),
    "ets_add_add_12": (
        "ExponentialSmoothing",
        {"trend": "add", "seasonal": "add", "season_length": 12},
        False,
        1e-4,
    ),
}

STRATEGIES = {
    "holdout": {"strategy": HOLDOUT_STRATEGY, "splits": HOLDOUT},
    "rolling": {"strategy": CV, "splits": ROLLING},
}

SCENARIOS = [(s, r) for s in STRATEGIES for r in RUNS]

#: Past the measured horizon of 3, so the warning shows too.
PREDICTED_HORIZON = 5


def _metrics(client, run_id: int) -> list:
    with client.app.container["session_factory"]() as db:
        rows = db.query(Metric).filter(Metric.run_id == run_id).all()
        return sorted(
            (
                [
                    row.split.value,
                    row.level.value,
                    row.name,
                    row.fold_index,
                    row.value,
                    row.std_value,
                    row.unavailable_reason,
                ]
                for row in rows
            ),
            key=lambda r: [str(x) for x in r[:4]],
        )


def _predict(client, run_id: int) -> dict:
    response = client.post(
        "/api/v1/predict/", json={"run_id": run_id, "horizon": PREDICTED_HORIZON}
    )
    assert response.status_code == 200, response.text
    answer = response.json()
    PredictJob(prediction_id=answer["id"]).run()
    prediction = _get(client, Prediction, answer["id"])
    assert prediction.status == PredictionStatus.FINISHED
    return {
        "unevaluated_steps": answer.get("unevaluated_steps"),
        "evaluated_horizon": answer.get("evaluated_horizon"),
        "saved": _saved_dataset(prediction.results_path),
    }


@pytest.fixture(scope="module", name="sessions")
def fixture_sessions(client, tmp_path_factory):
    # Shuffled, so the runs also sort the rows they are handed.
    frame = _monthly().sample(frac=1.0, random_state=0).reset_index(drop=True)
    return {
        name: _session(
            client, tmp_path_factory.mktemp(f"runs-net-{name}"), frame, **config
        )
        for name, config in STRATEGIES.items()
    }


@pytest.fixture(scope="module", autouse=True)
def _save_golden():
    yield
    GOLDEN.save()


@pytest.fixture(scope="module", name="trained")
def fixture_trained(client, sessions):
    from DashAI.back.job.model_job import ModelJob

    runs = {}
    for strategy, run in SCENARIOS:
        model, params, searched, _ = RUNS[run]
        run_id = _create_run(
            client,
            sessions[strategy],
            model,
            params,
            goal_metric="MAE" if searched else "",
            optimizer="OptunaOptimizer" if searched else "",
        )
        ModelJob(run_id=run_id).run()
        assert _get(client, Run, run_id).status == RunStatus.FINISHED
        runs[(strategy, run)] = run_id
    return runs


@pytest.mark.parametrize(("strategy", "run"), SCENARIOS)
def test_the_run_keeps_the_same_cuts_and_parameters(client, trained, strategy, run):
    stored = _get(client, Run, trained[(strategy, run)])

    GOLDEN.pin(
        f"{strategy}/{run}/run",
        {
            "split_indexes": json.loads(stored.split_indexes),
            "parameters": stored.parameters,
        },
    )


@pytest.mark.parametrize(("strategy", "run"), SCENARIOS)
def test_the_forecasts_file_is_the_same(client, trained, strategy, run):
    response = client.get(f"/api/v1/run/{trained[(strategy, run)]}/forecasts")

    assert response.status_code == 200, response.text
    GOLDEN.pin(f"{strategy}/{run}/forecasts", response.json(), RUNS[run][3])


@pytest.mark.parametrize(("strategy", "run"), SCENARIOS)
def test_the_run_scores_the_same(client, trained, strategy, run):
    GOLDEN.pin(
        f"{strategy}/{run}/metrics",
        _metrics(client, trained[(strategy, run)]),
        RUNS[run][3],
    )


@pytest.mark.parametrize(("strategy", "run"), SCENARIOS)
def test_the_prediction_declaration_is_the_same(client, trained, strategy, run):
    response = client.get(f"/api/v1/predict/splits/{trained[(strategy, run)]}")

    assert response.status_code == 200, response.text
    declared = response.json()
    declared.pop("training_dataset_id")  # an id, which depends on test order
    GOLDEN.pin(f"{strategy}/{run}/predict_splits", declared)


@pytest.mark.parametrize(("strategy", "run"), SCENARIOS)
def test_a_horizon_prediction_saves_the_same(client, trained, strategy, run):
    GOLDEN.pin(
        f"{strategy}/{run}/prediction",
        _predict(client, trained[(strategy, run)]),
        RUNS[run][3],
    )
