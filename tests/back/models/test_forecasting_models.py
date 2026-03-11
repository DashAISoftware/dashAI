import numpy as np
import pandas as pd
import pytest

from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.forecasting.prophet_model import (
    _patch_prophet_regressor_column_matrix,
)
from DashAI.back.models.forecasting.sklearn_multistep_forecaster import (
    SklearnMultiStepForecaster,
)
from DashAI.back.models.model_factory import ModelFactory


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
