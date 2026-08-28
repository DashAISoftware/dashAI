"""Forecasts must line up with the dates they were asked for.

A forecasting model used to read only how many rows it was handed and forecast
that many steps past the end of training. That is right for the partition that
directly follows training, and wrong for every later one: with a train,
validation and test split, the test partition was scored against a forecast of
the validation window, so every test metric was measured against the wrong
rows and looked far worse than the model deserved.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.enums.metrics import SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.models.forecasting.arima import ARIMA
from DashAI.back.models.forecasting.exponential_smoothing import ExponentialSmoothing
from DashAI.back.models.forecasting.naive import NaiveForecaster
from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

ALL_MODELS = [NaiveForecaster, SeasonalNaiveForecaster, ARIMA, ExponentialSmoothing]


def _split(n=50, freq="D"):
    """A perfectly linear daily series, split train / validation / test."""
    from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter

    dates = pd.date_range("2020-01-01", periods=n, freq=freq).strftime("%Y-%m-%d")
    dataset = transform_dataset_with_schema(
        to_dashai_dataset(
            pd.DataFrame({"date": dates.tolist(), "v": [float(i) for i in range(n)]})
        ),
        {
            "date": {"type": "Date", "dtype": "%Y-%m-%d"},
            "v": {"type": "Float", "dtype": "float64"},
        },
    )
    x, y = select_columns(dataset, ["date"], ["v"])
    splitter = TemporalHoldoutSplitter({"train": 0.6, "validation": 0.2, "test": 0.2})
    return splitter.split(x, y)


def _actual(y_split):
    return np.asarray(y_split.to_pandas().iloc[:, 0], dtype=float)


def test_the_test_partition_is_forecast_at_its_own_dates():
    # The regression this file exists for. On a perfectly linear series ARIMA
    # should land on the test values; before the fix it returned the
    # validation window and was off by exactly len(validation).
    xs, ys, _ = _split()
    model = ARIMA(p=1, d=1, q=0)
    model.train(xs["train"], ys["train"])

    forecast = np.asarray(model.predict(xs["test"]), dtype=float)

    assert forecast == pytest.approx(_actual(ys["test"]), abs=0.5)


def test_the_validation_partition_still_lines_up():
    xs, ys, _ = _split()
    model = ARIMA(p=1, d=1, q=0)
    model.train(xs["train"], ys["train"])

    forecast = np.asarray(model.predict(xs["validation"]), dtype=float)

    assert forecast == pytest.approx(_actual(ys["validation"]), abs=0.5)


def test_a_later_partition_is_further_ahead_than_an_earlier_one():
    # True of any model that does not forecast a flat line: the test window is
    # further from the training data than the validation window is.
    xs, ys, _ = _split()
    model = ARIMA(p=1, d=1, q=0)
    model.train(xs["train"], ys["train"])

    validation = np.asarray(model.predict(xs["validation"]), dtype=float)
    test = np.asarray(model.predict(xs["test"]), dtype=float)

    assert test[0] > validation[-1]


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_every_model_returns_one_value_per_requested_row(model_class):
    xs, ys, _ = _split()
    model = model_class()
    model.train(xs["train"], ys["train"])

    assert len(model.predict(xs["test"])) == len(xs["test"])


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_monthly_dates_are_counted_in_months_not_days(model_class):
    # The gap between one row and the next is 28 to 31 days, so a fixed day
    # count would drift. What matters is how many periods ahead a date is.
    xs, ys, _ = _split(n=48, freq="MS")
    model = model_class()
    model.train(xs["train"], ys["train"])

    forecast = np.asarray(model.predict(xs["test"]), dtype=float)

    assert len(forecast) == len(xs["test"])
    assert np.isfinite(forecast).all()


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_forecasting_models_record_no_train_metrics(model_class):
    # An in sample fit statistic invites comparison against test error, which
    # means nothing for a forecaster, so these models report none.
    model = model_class()
    xs, ys, _ = _split()
    model.train(xs["train"], ys["train"])

    assert model.calculate_metrics(split=SplitEnum.TRAIN) is None


@pytest.mark.parametrize("model_class", ALL_MODELS)
def test_asking_for_a_date_inside_the_training_range_is_refused(model_class):
    # These models forecast forward only. Returning something for a past date
    # would quietly produce a number that is not a forecast at all.
    xs, ys, _ = _split()
    model = model_class()
    model.train(xs["train"], ys["train"])

    with pytest.raises(ValueError, match="inside the training data"):
        model.predict(xs["train"])
