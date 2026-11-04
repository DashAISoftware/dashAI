"""The contract of a single-series forecaster, and what each model answers.

A forecaster is fitted on the values of a series in time order and forecasts a
number of steps past the end of them. It never reads a date.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.models.forecasting.arima import ARIMA
from DashAI.back.models.forecasting.drift import DriftForecaster
from DashAI.back.models.forecasting.exponential_smoothing import ExponentialSmoothing
from DashAI.back.models.forecasting.mean import MeanForecaster
from DashAI.back.models.forecasting.naive import NaiveForecaster
from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    Forecast,
    SingleSeriesForecastingModel,
)
from DashAI.back.models.forecasting.theta import Theta

ALL_MODELS = [
    NaiveForecaster,
    MeanForecaster,
    DriftForecaster,
    SeasonalNaiveForecaster,
    ARIMA,
    ExponentialSmoothing,
    Theta,
]
SERIES = np.arange(1.0, 31.0)


def _seasonal(n_seasons=4):
    season = [10.0, 20.0, 15.0, 30.0, 25.0, 5.0, 12.0, 18.0, 22.0, 28.0, 8.0, 16.0]
    trend = np.arange(12 * n_seasons) * 0.5
    noise = np.random.RandomState(0).normal(0.0, 1.0, size=12 * n_seasons)
    return np.asarray(season * n_seasons) + trend + noise


# --- the shared contract -----------------------------------------------------


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_every_model_forecasts_one_value_per_step(model_class):
    forecast = model_class().fit(SERIES).predict(4)

    assert isinstance(forecast, Forecast)
    assert len(forecast.point) == 4
    assert np.isfinite(forecast.point).all()
    assert forecast.lower == {}
    assert forecast.upper == {}


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_every_model_is_declared_for_the_single_series_task(model_class):
    assert model_class.COMPATIBLE_COMPONENTS == ["SingleSeriesForecastingTask"]
    assert issubclass(model_class, SingleSeriesForecastingModel)


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_every_model_round_trips_through_save_and_load(model_class, tmp_path):
    model = model_class().fit(SERIES)
    expected = model.predict(3).point

    path = tmp_path / "model.joblib"
    model.save(str(path))
    restored = model_class.load(str(path))

    assert list(restored.predict(3).point) == pytest.approx(list(expected))


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_predicting_before_fitting_is_refused(model_class):
    with pytest.raises(ValueError, match="Fit it before predicting"):
        model_class().predict(2)


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_a_model_refuses_dates_where_it_takes_steps(model_class):
    model = model_class().fit(SERIES)
    dates = to_dashai_dataset(pd.DataFrame({"date": ["2026-01-01", "2026-01-02"]}))

    with pytest.raises(TypeError, match="never reads dates"):
        model.predict(dates)


@pytest.mark.parametrize("model_class", ALL_MODELS)
@pytest.mark.parametrize("h", [0, -1])
def test_a_horizon_below_one_step_is_refused(model_class, h):
    with pytest.raises(ValueError, match="at least 1 step"):
        model_class().fit(SERIES).predict(h)


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_a_series_that_is_not_finite_is_a_wiring_error(model_class):
    with pytest.raises(ValueError, match="not finite"):
        model_class().fit([1.0, np.nan, 3.0])


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_train_fits_on_the_series_and_ignores_the_dates(model_class):
    dates = to_dashai_dataset(pd.DataFrame({"date": ["2026-01-01"] * len(SERIES)}))
    series = to_dashai_dataset(pd.DataFrame({"y": SERIES}))

    trained = model_class().train(dates, series)

    assert list(trained.predict(2).point) == pytest.approx(
        list(model_class().fit(SERIES).predict(2).point)
    )


# --- what each model declares ------------------------------------------------


def test_only_arima_takes_exogenous_variables():
    assert ARIMA.EXOGENOUS == "optional"
    for model_class in (NaiveForecaster, SeasonalNaiveForecaster, ExponentialSmoothing):
        assert model_class.EXOGENOUS == "none"
    # Published, so the session can mark the models that will not use them.
    for model_class in ALL_MODELS:
        assert model_class.get_metadata()["exogenous"] == model_class.EXOGENOUS


def test_a_model_that_takes_exogenous_variables_can_be_told_not_to():
    # The switch compares the same model with and without them, so it is a
    # choice of the run and never something a search tunes.
    field = ARIMA.get_schema()["properties"]["use_exogenous"]
    assert field["type"] == "boolean"
    assert field["placeholder"] is True
    assert "use_exogenous" not in NaiveForecaster.get_schema()["properties"]
    assert ARIMA().use_exogenous is True
    assert ARIMA(use_exogenous=False).use_exogenous is False


@pytest.mark.parametrize(
    ("x", "match"),
    [
        (np.arange(30.0), "one column per variable"),
        (np.full((30, 1), np.nan), "not finite"),
    ],
    ids=["one-dimensional", "not finite"],
)
def test_exogenous_variables_are_a_finite_matrix(x, match):
    with pytest.raises(ValueError, match=match):
        ARIMA(p=1, d=0, q=0).fit(SERIES, x=x)


def test_the_future_has_the_columns_the_model_was_fitted_on():
    steps = np.arange(len(SERIES), dtype=float)
    x = np.column_stack([np.sin(steps), np.cos(steps)])
    model = ARIMA(p=1, d=0, q=0).fit(SERIES, x=x)

    with pytest.raises(ValueError, match="2 exogenous variable"):
        model.predict(3, x_future=np.ones((3, 1)))


@pytest.mark.parametrize(
    ("model_class", "params", "has_exogenous", "used", "reason"),
    [
        (ARIMA, {}, True, True, None),
        (ARIMA, {"use_exogenous": False}, True, False, "exogenousSwitchedOff"),
        (ARIMA, {}, False, False, "sessionHasNoExogenous"),
        (NaiveForecaster, {}, True, False, "modelTakesNoExogenous"),
        (NaiveForecaster, {}, False, False, "sessionHasNoExogenous"),
    ],
)
def test_whether_a_run_uses_the_exogenous_variables(
    model_class, params, has_exogenous, used, reason
):
    from DashAI.back.models.forecasting.single_series_forecasting_model import (
        exogenous_usage,
    )

    uses, why = exogenous_usage(model_class, params, has_exogenous)

    assert uses is used
    assert (why or {}).get("key") == reason
    if why:
        assert why["values"] == {"model": model_class.__name__}


@pytest.mark.parametrize(
    ("record", "used"),
    [
        (None, False),
        ({"used": False, "columns": [], "reason": None}, False),
        ({"used": True, "columns": [{"name": "promo", "type": "Float"}]}, True),
    ],
)
def test_what_a_run_recorded_says_whether_it_read_exogenous_variables(record, used):
    """The one reader of ``Run.exogenous.used``: the prediction API and the
    prediction job ask it, so the two cannot disagree."""
    from types import SimpleNamespace

    from DashAI.back.models.forecasting.single_series_forecasting_model import (
        used_exogenous,
    )

    assert used_exogenous(SimpleNamespace(exogenous=record)) is used


def test_a_model_without_exogenous_variables_refuses_them():
    with pytest.raises(ValueError, match="uses no exogenous variables"):
        NaiveForecaster().fit(SERIES, x=np.ones((len(SERIES), 1)))


def test_exogenous_variables_need_one_row_per_step():
    model = ARIMA(p=1, d=0, q=0).fit(SERIES, x=np.arange(len(SERIES)).reshape(-1, 1))

    with pytest.raises(ValueError, match="2 row"):
        model.predict(3, x_future=np.ones((2, 1)))


def test_a_model_fitted_on_exogenous_variables_needs_their_future():
    x = np.random.RandomState(1).normal(size=(len(SERIES), 1))
    model = ARIMA(p=1, d=0, q=0).fit(SERIES, x=x)

    with pytest.raises(ValueError, match="fitted on 1 exogenous variable"):
        model.predict(3)


def test_a_model_kept_before_exogenous_variables_still_forecasts():
    """A model pickled before it counted its exogenous variables has no
    ``_n_exogenous``; it was fitted without them, and forecasts as before."""
    model = ARIMA(p=1, d=0, q=0).fit(SERIES)
    del model._n_exogenous

    assert len(model.predict(3).point) == 3


def test_arima_uses_exogenous_variables_when_given():
    x = np.random.RandomState(1).normal(size=(40, 1))
    y = 5.0 + 3.0 * x[:, 0]
    model = ARIMA(p=0, d=0, q=0).fit(y, x=x)

    future = np.array([[1.0], [-1.0]])

    assert model.predict(2, x_future=future).point == pytest.approx(
        [8.0, 2.0], abs=1e-3
    )


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_every_model_gives_nested_intervals_around_its_forecast(model_class):
    params = {"season_length": 12} if model_class is SeasonalNaiveForecaster else {}
    forecast = model_class(**params).fit(_seasonal()).predict(6, levels=[80, 95])

    for level in (80, 95):
        assert (forecast.lower[level] <= forecast.point).all()
        assert (forecast.point <= forecast.upper[level]).all()
    assert (forecast.lower[95] < forecast.lower[80]).all()
    assert (forecast.upper[95] > forecast.upper[80]).all()


@pytest.mark.parametrize("level", [0, 100, 150])
def test_a_level_outside_zero_and_a_hundred_is_refused(level):
    with pytest.raises(ValueError, match="between 0"):
        NaiveForecaster().fit(SERIES).predict(2, levels=[level])


def test_a_model_without_intervals_refuses_a_level():
    class _PointOnly(NaiveForecaster):
        SUPPORTS_INTERVALS = False

    with pytest.raises(ValueError, match="gives no prediction intervals"):
        _PointOnly().fit(SERIES).predict(2, levels=[80])


# --- the baselines, whose answers are exactly knowable ------------------------


def test_naive_carries_the_last_value_forward():
    forecast = NaiveForecaster().fit([10.0, 20.0, 35.0]).predict(3)

    assert list(forecast.point) == pytest.approx([35.0, 35.0, 35.0])


def test_naive_intervals_grow_with_the_square_root_of_the_step():
    # One-step changes of +10 and +15: sigma = sqrt((100 + 225) / 2).
    forecast = NaiveForecaster().fit([10.0, 20.0, 35.0]).predict(4, levels=[95])

    sigma = np.sqrt((100.0 + 225.0) / 2)
    half_width = forecast.upper[95] - forecast.point
    assert half_width == pytest.approx(1.959964 * sigma * np.sqrt([1, 2, 3, 4]))


def test_seasonal_naive_repeats_the_last_season():
    model = SeasonalNaiveForecaster(season_length=4)
    forecast = model.fit([1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]).predict(6)

    # The last full season is 10, 20, 30, 40, and it repeats from there.
    assert list(forecast.point) == pytest.approx([10.0, 20.0, 30.0, 40.0, 10.0, 20.0])


def test_seasonal_naive_intervals_widen_once_per_season():
    model = SeasonalNaiveForecaster(season_length=2)
    forecast = model.fit([1.0, 2.0, 4.0, 6.0]).predict(5, levels=[95])

    # Seasonal changes of +3 and +4: sigma = sqrt((9 + 16) / 2), and k = 0, 0,
    # 1, 1, 2 complete seasons before each step.
    sigma = np.sqrt((9.0 + 16.0) / 2)
    half_width = forecast.upper[95] - forecast.point
    expected = 1.959964 * sigma * np.sqrt([1, 1, 2, 2, 3])
    assert half_width == pytest.approx(expected)


def test_seasonal_naive_with_a_season_of_one_is_the_naive_forecast():
    model = SeasonalNaiveForecaster(season_length=1).fit([10.0, 20.0, 35.0])

    assert list(model.predict(2).point) == pytest.approx([35.0, 35.0])


def test_seasonal_naive_needs_a_full_season_of_history():
    with pytest.raises(ValueError, match="season"):
        SeasonalNaiveForecaster(season_length=12).fit([1.0, 2.0, 3.0])


def test_a_series_of_one_observation_has_no_spread_to_bound():
    forecast = NaiveForecaster().fit([5.0]).predict(2, levels=[80])

    assert np.isnan(forecast.lower[80]).all()


# --- the statsmodels wrappers ------------------------------------------------


def test_arima_follows_a_linear_trend():
    # A perfectly linear series with a first difference is something ARIMA
    # should extrapolate almost exactly.
    forecast = ARIMA(p=1, d=1, q=0).fit(np.arange(1.0, 41.0)).predict(3)

    assert forecast.point == pytest.approx([41.0, 42.0, 43.0], abs=0.5)


def test_arima_with_a_seasonal_part_repeats_the_season():
    season = [10.0, 20.0, 15.0, 30.0, 25.0, 5.0, 12.0, 18.0, 22.0, 28.0, 8.0, 16.0]
    model = ARIMA(
        p=0, d=0, q=0, seasonal_p=0, seasonal_d=1, seasonal_q=0, season_length=12
    )

    forecast = model.fit(np.asarray(season * 4)).predict(12)

    assert forecast.point == pytest.approx(season, abs=1e-6)


def test_a_seasonal_part_needs_a_season_of_at_least_two():
    with pytest.raises(ValueError, match="season length of at least 2"):
        ARIMA(seasonal_p=1, season_length=1)


def test_exponential_smoothing_tracks_the_level_of_a_flat_series():
    forecast = ExponentialSmoothing().fit([5.0] * 30).predict(3)

    assert forecast.point == pytest.approx([5.0, 5.0, 5.0], abs=0.1)


def test_exponential_smoothing_can_use_a_seasonal_component():
    season = [10.0, 20.0, 30.0, 40.0]
    model = ExponentialSmoothing(seasonal="add", season_length=4)

    forecast = model.fit(season * 8).predict(4)

    assert forecast.point == pytest.approx(season, abs=1.0)


def test_a_multiplicative_trend_gives_the_same_intervals_every_time():
    # No closed form: statsmodels simulates them, with a fixed seed.
    series = 50.0 * 1.02 ** np.arange(36)
    model = ExponentialSmoothing(trend="mul").fit(series)

    first = model.predict(3, levels=[80])
    second = model.predict(3, levels=[80])

    assert list(first.lower[80]) == list(second.lower[80])


@pytest.mark.parametrize(("theta", "slope"), [(1.0, 0.0), (2.0, 0.5)])
def test_theta_follows_its_share_of_a_linear_trend(theta, slope):
    # On a line rising 1 per step, theta 1 forecasts flat and the classical
    # theta 2 follows half of the slope.
    forecast = Theta(theta=theta).fit(SERIES).predict(4)

    assert np.diff(forecast.point) == pytest.approx([slope] * 3, abs=1e-3)


def test_theta_can_use_a_seasonal_component():
    season = [10.0, 20.0, 30.0, 40.0]
    model = Theta(seasonal="add", season_length=4, theta=1.0)

    forecast = model.fit(season * 8).predict(4)

    assert forecast.point == pytest.approx(season, abs=1.0)


def test_theta_intervals_cover_what_they_promise():
    # The Theta method is simple exponential smoothing with drift. On series
    # drawn from that model, an 80% interval should hold about 80% of the
    # values to come. statsmodels' own intervals square alpha - 1 instead of
    # alpha, and with alpha 0.2 they hold about 98% six steps ahead.
    rng = np.random.default_rng(0)
    alpha, n, h, reps = 0.2, 120, 6, 200
    inside = 0
    for _ in range(reps):
        noise = rng.normal(0.0, 1.0, n + h + 1)
        series = 100.0 + np.cumsum(0.3 + noise[1:] - (1 - alpha) * noise[:-1])
        forecast = Theta().fit(series[:n]).predict(h, levels=[80])
        actual = series[n + h - 1]
        inside += forecast.lower[80][-1] <= actual <= forecast.upper[80][-1]

    assert 0.72 <= inside / reps <= 0.88


def test_mean_forecasts_the_average_with_intervals_of_one_width():
    series = [2.0, 4.0, 3.0, 5.0, 6.0, 8.0]
    forecast = MeanForecaster().fit(series).predict(3, levels=[80])

    assert forecast.point == pytest.approx([28.0 / 6] * 3)
    width = forecast.upper[80] - forecast.lower[80]
    assert width == pytest.approx([width[0]] * 3)


def test_drift_extends_the_line_from_the_first_value_to_the_last():
    series = [2.0, 4.0, 3.0, 5.0, 6.0, 8.0]
    forecast = DriftForecaster().fit(series).predict(3, levels=[80])

    # Slope (8 - 2) / 5 = 1.2 per step, carried on from the last value.
    assert forecast.point == pytest.approx([9.2, 10.4, 11.6])
    assert (np.diff(forecast.upper[80] - forecast.lower[80]) > 0).all()


def test_drift_needs_two_observations_to_measure_a_slope():
    with pytest.raises(ValueError, match="at least 2 observations"):
        DriftForecaster().fit([5.0])
