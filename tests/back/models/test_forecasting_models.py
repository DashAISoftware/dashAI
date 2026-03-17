import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.forecasting.prophet_model import (
    ProphetModel,
    _patch_prophet_regressor_column_matrix,
)
from DashAI.back.models.forecasting.sklearn_multistep_forecaster import (
    SklearnMultiStepForecaster,
)
from DashAI.back.models.forecasting.statsmodels_arima_model import (
    StatsmodelsARIMAModel,
)
from DashAI.back.models.model_factory import ModelFactory

# ---------------------------------------------------------------------------
# Registry fixture (required by conftest client fixture)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            SklearnMultiStepForecaster,
        ]
    )

    monkeypatch.setitem(
        container._services,
        "component_registry",
        test_registry,
    )
    return test_registry


# ---------------------------------------------------------------------------
# Shared data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def daily_series():
    """200 days of synthetic daily temperature data (sinusoidal + noise)."""
    n = 200
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    np.random.seed(42)
    values = 15 + 10 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.randn(n)

    x_df = pd.DataFrame({"date": dates.astype(str)})
    y_df = pd.DataFrame({"temp": values})

    metadata = {
        "timestamp_col": "date",
        "target_col": "temp",
        "exog_cols": [],
        "frequency": "D",
    }

    return {
        "x": to_dashai_dataset(x_df),
        "y": to_dashai_dataset(y_df),
        "x_df": x_df,
        "y_df": y_df,
        "dates": dates,
        "values": values,
        "metadata": metadata,
    }


@pytest.fixture(scope="module")
def small_series():
    """Small dataset (12 rows) to test auto window-size adjustment."""
    n = 12
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    values = np.arange(n, dtype=float)

    x_df = pd.DataFrame({"date": dates.astype(str)})
    y_df = pd.DataFrame({"temp": values})

    metadata = {
        "timestamp_col": "date",
        "target_col": "temp",
        "exog_cols": [],
        "frequency": "D",
    }

    return {
        "x": to_dashai_dataset(x_df),
        "y": to_dashai_dataset(y_df),
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Original tests (kept intact)
# ---------------------------------------------------------------------------


def test_forecasting_model_factory_can_instantiate_model():
    factory = ModelFactory(
        SklearnMultiStepForecaster,
        {
            "base_estimator": "linear",
            "window_size": 3,
            "forecast_strategy": "direct",
        },
    )

    assert isinstance(factory.model, SklearnMultiStepForecaster)


def test_prophet_patch_preserves_weekly_periodicity():
    Prophet = _patch_prophet_regressor_column_matrix()

    dates = pd.Series(pd.date_range("2024-01-01", periods=14, freq="D"))
    features = Prophet.fourier_series(dates, period=7, series_order=3)

    assert np.allclose(features[0], features[7], atol=1e-9)
    assert np.allclose(features[1], features[8], atol=1e-9)


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — estimator variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("estimator", ["linear", "ridge", "random_forest"])
def test_sklearn_estimators_fit_and_predict_outsample(daily_series, estimator):
    """All three base estimators should fit and produce out-of-sample forecasts."""
    model = SklearnMultiStepForecaster(
        base_estimator=estimator, window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=10,
    )

    preds = model.predict(periods=10)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == 10
    assert not np.all(np.isnan(preds))


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — strategies
# ---------------------------------------------------------------------------


def test_sklearn_direct_strategy_produces_forecast(daily_series):
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="direct"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=7,
    )
    preds = model.predict(periods=7)
    assert len(preds) == 7


def test_sklearn_recursive_strategy_produces_forecast(daily_series):
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=7,
    )
    preds = model.predict(periods=7)
    assert len(preds) == 7


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — in-sample predictions
# ---------------------------------------------------------------------------


def test_sklearn_insample_predictions_shape(daily_series):
    """In-sample predictions should have the same length as the input slice."""
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=10,
    )

    # Use a slice of the training x_df as in-sample input
    x_slice = daily_series["x_df"].iloc[10:30].copy()
    preds = model.predict(x_pred=x_slice)
    assert len(preds) == len(x_slice)


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — auto window-size adjustment
# ---------------------------------------------------------------------------


def test_sklearn_auto_adjusts_window_size_for_small_dataset(small_series):
    """Model should not raise when window_size > available samples."""
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=20, forecast_strategy="recursive"
    )
    # Should not raise — window_size is auto-adjusted internally
    model.fit(
        small_series["x"],
        small_series["y"],
        temporal_metadata=small_series["metadata"],
        horizon=2,
    )
    assert model.window_size < 20  # was reduced


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — forecast uncertainty & components
# ---------------------------------------------------------------------------


def test_sklearn_forecast_uncertainty_columns(daily_series):
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=10,
    )

    result = model.get_forecast_uncertainty(horizon=10)
    assert set(result.columns) >= {"ds", "yhat", "yhat_lower", "yhat_upper"}
    assert len(result) == 10
    assert (result["yhat_upper"] >= result["yhat_lower"]).all()


def test_sklearn_forecast_components_columns(daily_series):
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=10,
    )

    result = model.get_forecast_components(horizon=10)
    assert "ds" in result.columns
    assert "trend" in result.columns
    assert "residual" in result.columns
    assert len(result) == 10


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — save / load
# ---------------------------------------------------------------------------


def test_sklearn_save_and_load_preserves_predictions(daily_series):
    model = SklearnMultiStepForecaster(
        base_estimator="linear", window_size=5, forecast_strategy="recursive"
    )
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=5,
    )
    preds_before = model.predict(periods=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sklearn_model.pkl")
        model.save(path)

        loaded = SklearnMultiStepForecaster()
        loaded.load(path)

    preds_after = loaded.predict(periods=5)
    np.testing.assert_array_almost_equal(preds_before, preds_after)


# ---------------------------------------------------------------------------
# SklearnMultiStepForecaster — edge cases
# ---------------------------------------------------------------------------


def test_sklearn_predict_before_fit_raises():
    model = SklearnMultiStepForecaster()
    with pytest.raises(ValueError, match="Model not fitted"):
        model.predict(periods=5)


def test_sklearn_negative_periods_raises(daily_series):
    model = SklearnMultiStepForecaster(window_size=5)
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
        horizon=5,
    )
    with pytest.raises(ValueError, match="Prediction horizon must be a positive"):
        model.predict(periods=-1)


# ---------------------------------------------------------------------------
# StatsmodelsARIMAModel
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fitted_arima(daily_series):
    model = StatsmodelsARIMAModel(p=1, d=1, q=1, trend="n")
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
    )
    return model


def test_arima_fit_stores_model(fitted_arima):
    assert fitted_arima.model_fit is not None


def test_arima_outsample_forecast_shape(fitted_arima):
    preds = fitted_arima.predict(periods=10)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == 10
    assert not np.all(np.isnan(preds))


def test_arima_insample_predict_shape(daily_series, fitted_arima):
    x_slice = daily_series["x_df"].iloc[5:20].copy()
    preds = fitted_arima.predict(x_pred=x_slice)
    assert len(preds) == len(x_slice)


def test_arima_forecast_uncertainty_columns(fitted_arima):
    result = fitted_arima.get_forecast_uncertainty(horizon=10)
    assert set(result.columns) >= {"ds", "yhat", "yhat_lower", "yhat_upper"}
    assert len(result) == 10
    assert (result["yhat_upper"] >= result["yhat_lower"]).all()


def test_arima_forecast_components_columns(fitted_arima):
    result = fitted_arima.get_forecast_components(horizon=10)
    assert "ds" in result.columns
    assert "trend" in result.columns
    assert "residual" in result.columns
    assert len(result) == 10


def test_arima_save_and_load_preserves_predictions(daily_series):
    model = StatsmodelsARIMAModel(p=1, d=1, q=1, trend="n")
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
    )
    preds_before = model.predict(periods=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "arima_model.pkl")
        model.save(path)

        loaded = StatsmodelsARIMAModel()
        loaded.load(path)

    preds_after = loaded.predict(periods=5)
    np.testing.assert_array_almost_equal(preds_before, preds_after)


def test_arima_predict_before_fit_raises():
    model = StatsmodelsARIMAModel()
    with pytest.raises(ValueError, match="not fitted"):
        model.predict(periods=5)


@pytest.mark.parametrize("order", [(1, 0, 0), (0, 1, 1), (2, 1, 0)])
def test_arima_different_orders_fit(daily_series, order):
    """Various ARIMA orders should fit without error."""
    p, d, q = order
    model = StatsmodelsARIMAModel(p=p, d=d, q=q, trend="n")
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
    )
    assert model.model_fit is not None


# ---------------------------------------------------------------------------
# ProphetModel
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fitted_prophet(daily_series):
    model = ProphetModel()
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
    )
    return model


def test_prophet_fit_stores_model(fitted_prophet):
    assert fitted_prophet.model is not None


def test_prophet_outsample_forecast_shape(fitted_prophet):
    preds = fitted_prophet.predict(periods=30)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == 30
    assert not np.all(np.isnan(preds))


def test_prophet_insample_predict_shape(daily_series, fitted_prophet):
    x_slice = daily_series["x_df"].iloc[:20].copy()
    preds = fitted_prophet.predict(x_pred=x_slice)
    assert len(preds) == len(x_slice)


def test_prophet_forecast_uncertainty_columns(fitted_prophet):
    result = fitted_prophet.get_forecast_uncertainty(horizon=14)
    assert set(result.columns) >= {"ds", "yhat", "yhat_lower", "yhat_upper"}
    assert len(result) == 14
    assert (result["yhat_upper"] >= result["yhat_lower"]).all()


def test_prophet_forecast_components_columns(fitted_prophet):
    result = fitted_prophet.get_forecast_components(horizon=14)
    assert "ds" in result.columns
    assert "trend" in result.columns
    assert len(result) == 14


def test_prophet_save_and_load_preserves_predictions(daily_series):
    model = ProphetModel()
    model.fit(
        daily_series["x"],
        daily_series["y"],
        temporal_metadata=daily_series["metadata"],
    )
    preds_before = model.predict(periods=7)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prophet_model.pkl")
        model.save(path)

        loaded = ProphetModel()
        loaded.load(path)

    preds_after = loaded.predict(periods=7)
    np.testing.assert_array_almost_equal(preds_before, preds_after)
