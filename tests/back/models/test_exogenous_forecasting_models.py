import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.models.forecasting.arima import ARIMA
from DashAI.back.models.forecasting.exogenous_linear_regression import (
    ExogenousLinearRegression,
)
from DashAI.back.models.forecasting.exponential_smoothing import ExponentialSmoothing
from DashAI.back.models.forecasting.naive import NaiveForecaster
from DashAI.back.models.forecasting.sarimax import SARIMAX
from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

EXOGENOUS_MODELS = [ARIMA, SARIMAX, ExogenousLinearRegression]
HISTORY_ONLY_MODELS = [NaiveForecaster, SeasonalNaiveForecaster, ExponentialSmoothing]
BOTH_TASK_MODELS = [ARIMA, SARIMAX]

TYPES = {
    "date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "price": {"type": "Float", "dtype": "float64"},
    "promo": {"type": "Integer", "dtype": "int64"},
}


def _dates(n, start=0):
    return [f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(start, start + n)]


def _x(n, start=0, with_exogenous=True):
    columns = {"date": _dates(n, start)}
    if with_exogenous:
        columns["price"] = [float(10 + i) for i in range(start, start + n)]
        columns["promo"] = [i % 2 for i in range(start, start + n)]
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame(columns)),
        {name: TYPES[name] for name in columns},
    )


def _y(values):
    return to_dashai_dataset(pd.DataFrame({"target": [float(v) for v in values]}))


def _series(n):
    return [3.0 * (10 + i) + 2.0 * (i % 2) for i in range(n)]


def _fit(model, n=40, with_exogenous=True):
    model._trained_on = n
    return model.train(_x(n, with_exogenous=with_exogenous), _y(_series(n)))


def _future(model, steps, with_exogenous=True):
    return _x(steps, start=model._trained_on, with_exogenous=with_exogenous)


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_every_exogenous_model_serves_the_exogenous_task(model_class):
    assert "ExogenousForecastingTask" in model_class.COMPATIBLE_COMPONENTS
    assert model_class.SUPPORTS_EXOGENOUS is True


@pytest.mark.parametrize("model_class", BOTH_TASK_MODELS)
def test_a_model_that_can_do_without_variables_serves_both_tasks(model_class):
    assert model_class.COMPATIBLE_COMPONENTS == [
        "ForecastingTask",
        "ExogenousForecastingTask",
    ]


@pytest.mark.parametrize("model_class", HISTORY_ONLY_MODELS)
def test_a_model_that_reads_only_the_date_stays_out_of_the_exogenous_task(model_class):
    assert model_class.COMPATIBLE_COMPONENTS == ["ForecastingTask"]
    assert model_class.SUPPORTS_EXOGENOUS is False


def test_a_model_that_needs_variables_is_not_offered_the_plain_task():
    assert ExogenousLinearRegression.COMPATIBLE_COMPONENTS == [
        "ExogenousForecastingTask"
    ]


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_every_exogenous_model_forecasts_one_value_per_requested_row(model_class):
    model = _fit(model_class())

    forecast = model.predict(_future(model, 4))

    assert len(forecast) == 4
    assert np.isfinite(np.asarray(forecast, dtype=float)).all()


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_the_variables_change_the_forecast(model_class):
    model = _fit(model_class())
    rows = _future(model, 3)

    doubled = rows.to_pandas()
    doubled["price"] = doubled["price"] * 2
    doubled = transform_dataset_with_schema(to_dashai_dataset(doubled), TYPES)

    assert not np.allclose(
        np.asarray(model.predict(rows), dtype=float),
        np.asarray(model.predict(doubled), dtype=float),
    )


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_a_forecast_far_ahead_reads_the_variables_of_its_own_rows(model_class):
    model = _fit(model_class())
    far = _x(3, start=model._trained_on + 10)

    forecast = np.asarray(model.predict(far), dtype=float)

    assert len(forecast) == 3
    assert np.isfinite(forecast).all()


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_the_filled_gap_never_reaches_the_requested_rows(model_class):
    model = _fit(model_class())
    tail = np.array([[200.0, 0.0], [201.0, 1.0], [202.0, 0.0]])
    horizon = 23

    scaffolding = {
        "flat": np.tile(tail[0], (horizon - len(tail), 1)),
        "wild": np.tile([-5000.0, 99.0], (horizon - len(tail), 1)),
        "zero": np.zeros((horizon - len(tail), 2)),
    }
    forecasts = {
        label: np.asarray(model._forecast(horizon, np.vstack([gap, tail])))[-3:]
        for label, gap in scaffolding.items()
    }

    assert list(forecasts["wild"]) == pytest.approx(list(forecasts["flat"]))
    assert list(forecasts["zero"]) == pytest.approx(list(forecasts["flat"]))


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_a_missing_variable_is_refused_rather_than_ignored(model_class):
    model = _fit(model_class())
    without = _x(3, start=model._trained_on, with_exogenous=False)

    with pytest.raises(ValueError, match="not among the columns"):
        model.predict(without)


@pytest.mark.parametrize("model_class", EXOGENOUS_MODELS)
def test_every_exogenous_model_round_trips_through_save_and_load(model_class, tmp_path):
    model = _fit(model_class())
    expected = list(np.asarray(model.predict(_future(model, 3)), dtype=float))

    path = tmp_path / "model.joblib"
    model.save(str(path))
    restored = model_class.load(str(path))

    assert list(
        np.asarray(restored.predict(_future(model, 3)), dtype=float)
    ) == pytest.approx(expected)


@pytest.mark.parametrize("model_class", BOTH_TASK_MODELS)
def test_a_dual_model_still_forecasts_from_the_date_alone(model_class):
    model = _fit(model_class(), with_exogenous=False)

    forecast = model.predict(_future(model, 4, with_exogenous=False))

    assert len(forecast) == 4
    assert np.isfinite(np.asarray(forecast, dtype=float)).all()


def test_the_linear_model_refuses_a_date_with_nothing_beside_it():
    with pytest.raises(ValueError, match="explanatory"):
        _fit(ExogenousLinearRegression(), with_exogenous=False)


def test_the_linear_model_recovers_a_linear_relationship():
    model = _fit(ExogenousLinearRegression(include_trend=False), n=40)

    forecast = np.asarray(model.predict(_future(model, 3)), dtype=float)
    expected = _series(43)[40:]

    assert list(forecast) == pytest.approx(expected, abs=1e-6)


def test_sarimax_without_a_season_length_models_no_season():
    assert SARIMAX(season_length=1)._seasonal_order == (0, 0, 0, 0)
    assert SARIMAX(season_length=0, seasonal_d=1)._seasonal_order == (0, 0, 0, 0)
    assert SARIMAX(season_length=4, seasonal_d=1)._seasonal_order == (0, 1, 0, 4)


def test_sarimax_refuses_a_season_it_cannot_see_twice():
    with pytest.raises(ValueError, match="seen twice"):
        _fit(SARIMAX(season_length=12), n=20)


def test_a_history_only_model_ignores_variables_it_is_handed():
    model = NaiveForecaster()
    model._trained_on = 30
    model.train(_x(30), _y(_series(30)))

    assert model._exogenous_columns == []
    assert len(model.predict(_future(model, 2))) == 2
