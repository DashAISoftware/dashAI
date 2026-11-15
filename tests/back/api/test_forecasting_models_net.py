"""Regression net for the reduction model PR (RECONCILING_FORECASTING §8.3).

Recorded on develop ``7b04bcc9c``, before the PR touches anything, with
``DASHAI_RECORD_FORECASTING_MODELS_NET=1``, and compared against that file on
every slice after: a diff on the golden is a behaviour change. It pins three
things the PR must not move:

- **The forecasts and intervals of the seven registered forecasters**, fitted
  on the clean series of the core net. Until now only the runs net pinned
  intervals, and only for four of them.
- **The score of a search trial**, for each forecaster. The PR stops trials
  from asking for intervals (§2.15, detail 7), which must leave every score
  where it was.
- **The scikit-learn regressors, as x/y models**: their hyperparameters as
  built for a run, which is what the reduction model reads from them, and
  what they predict. The reduction model extracts a plain scikit-learn
  estimator from them and must leave them untouched.

ARIMA, ETS and Theta are fitted by numerical optimisation, whose last digits
depend on the platform's BLAS (see ``test_forecasting_core_net.py``), so they
are compared to a looser relative tolerance; everything else to 1e-9.

Lives under ``tests/back/api`` to reuse the ``client`` fixture, whose
container holds the registry the regressors are built from.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.metrics.regression.mae import MAE
from DashAI.back.metrics.regression.rmse import RMSE
from DashAI.back.models.forecasting.arima import ARIMA
from DashAI.back.models.forecasting.drift import DriftForecaster
from DashAI.back.models.forecasting.exponential_smoothing import ExponentialSmoothing
from DashAI.back.models.forecasting.mean import MeanForecaster
from DashAI.back.models.forecasting.naive import NaiveForecaster
from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster
from DashAI.back.models.forecasting.theta import Theta
from DashAI.back.splitters.rolling_origin import RollingOriginSplitter
from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter
from DashAI.back.tasks.time_grid import TimeGrid
from DashAI.back.units.backtest_forecaster_unit import BacktestForecasterUnit
from tests.back.api.golden_net import Golden
from tests.back.api.test_forecasting_core_net import SERIES

GOLDEN = Golden(
    Path(__file__).with_name("forecasting_models_net_golden.json"),
    "DASHAI_RECORD_FORECASTING_MODELS_NET",
)

HORIZON = 6
LEVELS = [80, 95]
FREQ = {"monthly": "MS", "daily": "D"}

#: Fitted by numerical optimisation: the relative tolerance their values are
#: compared to, the same as the core net's for ARIMA and ETS.
TOLERANCES = {ARIMA: 1e-6, ExponentialSmoothing: 1e-4, Theta: 1e-4}


@pytest.fixture(scope="module", autouse=True)
def _save_golden():
    yield
    GOLDEN.save()


def _values(series: str) -> np.ndarray:
    return SERIES[series]()["sales"].to_numpy(dtype=float)


def _promo(n: int) -> np.ndarray:
    """A planned promotion every third step: a fixed exogenous column."""
    return np.array([1.0 if i % 3 == 1 else 0.0 for i in range(n)]).reshape(-1, 1)


# --------------------------------------------------------------------------- #
# 1. The forecasts and intervals of the seven forecasters
# --------------------------------------------------------------------------- #

MODEL_CASES = {
    "naive": (NaiveForecaster, {}),
    "mean": (MeanForecaster, {}),
    "drift": (DriftForecaster, {}),
    "seasonal_naive": (SeasonalNaiveForecaster, {"season_length": "season"}),
    "arima_110": (ARIMA, {"p": 1, "d": 1, "q": 0}),
    "arima_211": (ARIMA, {"p": 2, "d": 1, "q": 1}),
    "ets_add_add": (
        ExponentialSmoothing,
        {"trend": "add", "seasonal": "add", "season_length": "season"},
    ),
    "ets_mul_trend": (ExponentialSmoothing, {"trend": "mul"}),
    "theta": (Theta, {}),
}
SEASONS = {"monthly": 12, "daily": 7}


def _params(params: dict, series: str) -> dict:
    """The case's parameters, with ``"season"`` read as the series' season."""
    return {
        key: SEASONS[series] if value == "season" else value
        for key, value in params.items()
    }


def _pin_forecast(key, model_class, forecast) -> None:
    value = {
        "point": forecast.point,
        "lower": forecast.lower,
        "upper": forecast.upper,
    }
    GOLDEN.pin(key, value, rel_tol=TOLERANCES.get(model_class, 1e-9))


@pytest.mark.parametrize("series", list(SERIES))
@pytest.mark.parametrize("case", list(MODEL_CASES))
def test_a_forecaster_forecasts_and_bounds_a_clean_series_the_same(series, case):
    model_class, params = MODEL_CASES[case]
    model = model_class(**_params(params, series)).fit(_values(series))

    forecast = model.predict(HORIZON, levels=LEVELS)

    _pin_forecast(f"forecast/{series}/{case}", model_class, forecast)


@pytest.mark.parametrize("series", list(SERIES))
def test_arima_forecasts_and_bounds_with_an_exogenous_column_the_same(series):
    values = _values(series)
    x = _promo(len(values) + HORIZON)
    model = ARIMA(p=1, d=1, q=0).fit(values, x[: len(values)])

    forecast = model.predict(HORIZON, x_future=x[len(values) :], levels=LEVELS)

    _pin_forecast(f"forecast/{series}/arima_110_promo", ARIMA, forecast)


# --------------------------------------------------------------------------- #
# 2. The score of a search trial
# --------------------------------------------------------------------------- #

SPLITTERS = {
    "holdout": lambda: TemporalHoldoutSplitter({"horizon": HORIZON}),
    "rolling": lambda: RollingOriginSplitter({"horizon": HORIZON, "n_origins": 3}),
}
TRIAL_CASES = {
    "naive": MODEL_CASES["naive"],
    "mean": MODEL_CASES["mean"],
    "drift": MODEL_CASES["drift"],
    "seasonal_naive": MODEL_CASES["seasonal_naive"],
    "arima_110": MODEL_CASES["arima_110"],
    "ets_add_add": MODEL_CASES["ets_add_add"],
    "theta": MODEL_CASES["theta"],
}
# MASE is switched off (#997), so the trials are scored with the two point
# metrics a search can optimise.
METRICS = {"MAE": MAE, "RMSE": RMSE}


def _grid(series: str, n_steps: int) -> TimeGrid:
    dates = pd.to_datetime(SERIES[series]()["date"])
    return TimeGrid(
        freq=FREQ[series], first=dates.iloc[0], last=dates.iloc[-1], n_steps=n_steps
    )


def _exogenous(cuts: dict, x=None) -> dict:
    """What ``ApplyCutPreprocessingUnit`` publishes: the same cut each time."""

    def cut(name):
        if x is None:
            return {"name": name, "columns": [], "values": np.empty((len(x_rows), 0))}
        return {"name": name, "columns": ["promo"], "values": x}

    x_rows = range(cuts["n_steps"])
    origins = cuts["validation_origins"]
    return {
        "declared": x is not None,
        "validation": [cut(f"origin_{i}") for i in range(len(origins))],
        "test": cut("test"),
        "final": cut("final"),
    }


def _trial_score(model, series: str, splitter: str, metric, x=None) -> float:
    values = _values(series)
    cuts = SPLITTERS[splitter]().cuts(len(values))
    unit = BacktestForecasterUnit(
        optimizer={"component": "", "params": {}},
        goal_metric="",
        run_id=None,
        artifact_prefix="net",
    )
    return unit._score_one_trial(
        model,
        values,
        cuts,
        metric,
        _grid(series, len(values)),
        _exogenous(cuts, x),
    )


@pytest.mark.parametrize("metric", list(METRICS))
@pytest.mark.parametrize("splitter", list(SPLITTERS))
@pytest.mark.parametrize("series", list(SERIES))
@pytest.mark.parametrize("case", list(TRIAL_CASES))
def test_a_search_trial_scores_a_forecaster_the_same(case, series, splitter, metric):
    model_class, params = TRIAL_CASES[case]
    model = model_class(**_params(params, series))

    score = _trial_score(model, series, splitter, METRICS[metric])

    GOLDEN.pin(
        f"trial/{series}/{splitter}/{case}/{metric}",
        score,
        rel_tol=TOLERANCES.get(model_class, 1e-9),
    )


@pytest.mark.parametrize("splitter", list(SPLITTERS))
def test_a_search_trial_scores_arima_with_an_exogenous_column_the_same(splitter):
    values = _values("monthly")

    score = _trial_score(
        ARIMA(p=1, d=1, q=0), "monthly", splitter, MAE, x=_promo(len(values))
    )

    GOLDEN.pin(f"trial/monthly/{splitter}/arima_110_promo/MAE", score, rel_tol=1e-6)


# --------------------------------------------------------------------------- #
# 3. The scikit-learn regressors, as x/y models
# --------------------------------------------------------------------------- #

#: Every registered regressor that is also a scikit-learn estimator: the ones
#: the reduction model offers. ``MLPRegression`` is torch and is not one.
SKLEARN_REGRESSORS = [
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
]


@pytest.fixture(name="registry")
def fixture_registry(client):
    return client.app.container["component_registry"]


def test_the_registered_scikit_learn_regressors_are_these(registry):
    names = sorted(
        component["name"]
        for component in registry.get_child_components(
            "SklearnLikeRegressor", recursive=True
        )
    )

    assert names == sorted(SKLEARN_REGRESSORS)


def _regressor(registry, name: str):
    """The regressor as a run builds it: its schema defaults, seeded."""
    from DashAI.back.core.schema_fields.defaults import resolve_component_defaults
    from DashAI.back.models.model_factory import ModelFactory

    params = resolve_component_defaults(name, registry)
    if "random_state" in params:
        params["random_state"] = 0
    return ModelFactory(registry[name]["class"], params, None).model


def _jsonable(value):
    """A JSON value for a hyperparameter, its ``repr`` when it has none."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return repr(value)


def _xy():
    """Forty rows of three numeric features and a target, with fixed noise."""
    rng = np.random.RandomState(3)
    x = rng.normal(size=(40, 3))
    y = 2.0 * x[:, 0] - x[:, 1] + 0.5 * x[:, 2] ** 2 + rng.normal(0.0, 0.1, 40)
    frame = pd.DataFrame({"a": x[:, 0], "b": x[:, 1], "c": x[:, 2], "y": y})
    dataset = transform_dataset_with_schema(
        to_dashai_dataset(frame),
        {name: {"type": "Float", "dtype": "float64"} for name in frame.columns},
    )
    return (
        dataset.select_columns(["a", "b", "c"]),
        dataset.select_columns(["y"]),
    )


@pytest.mark.parametrize("name", SKLEARN_REGRESSORS)
def test_a_regressor_is_built_with_the_same_hyperparameters(registry, name):
    model = _regressor(registry, name)

    hyperparameters = {
        key: _jsonable(value)
        for key, value in sorted(vars(model).items())
        if not key.startswith("_")
    }

    GOLDEN.pin(f"regressor/{name}/hyperparameters", hyperparameters)


@pytest.mark.parametrize("name", SKLEARN_REGRESSORS)
def test_a_regressor_predicts_the_same(registry, name):
    x, y = _xy()
    model = _regressor(registry, name)

    model.train(x, y)

    GOLDEN.pin(
        f"regressor/{name}/predictions",
        np.asarray(model.predict(x), dtype=float).ravel(),
    )
