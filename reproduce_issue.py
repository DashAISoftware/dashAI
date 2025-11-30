import numpy as np
import pandas as pd

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.models.forecasting.prophet_model import ProphetModel
from DashAI.back.models.forecasting.sklearn_multistep_forecaster import (
    SklearnMultiStepForecaster,
)


def create_dummy_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    values = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    data = pd.DataFrame({"ds": dates, "y": values})
    return to_dashai_dataset(data)


def test_sklearn_forecaster():
    print("\nTesting SklearnMultiStepForecaster...")
    dataset = create_dummy_data()

    # Create x (features) and y (target) datasets
    x_df = dataset.to_pandas()
    y_df = x_df[["y"]]
    y_dataset = to_dashai_dataset(y_df)

    model = SklearnMultiStepForecaster(window_size=5)

    # Metadata usually comes from task, mocking it here
    temporal_metadata = {"timestamp_col": "ds", "target_col": "y", "frequency": "D"}

    model.fit(dataset, y_dataset, temporal_metadata=temporal_metadata)

    # Test 1: predict with periods (standard)
    try:
        pred = model.predict(periods=5)
        print(f"✅ predict(periods=5) successful. Shape: {pred.shape}")
    except Exception as e:
        print(f"❌ predict(periods=5) failed: {e}")

    # Test 2: predict with horizon (alias)
    try:
        pred = model.predict(horizon=5)
        print(f"✅ predict(horizon=5) successful (alias). Shape: {pred.shape}")
    except Exception as e:
        print(f"❌ predict(horizon=5) failed: {e}")


def test_prophet_model():
    print("\nTesting ProphetModel...")
    dataset = create_dummy_data()

    # Create x (features) and y (target) datasets
    x_df = dataset.to_pandas()
    y_df = x_df[["y"]]
    y_dataset = to_dashai_dataset(y_df)

    model = ProphetModel()

    # Metadata usually comes from task, mocking it here
    temporal_metadata = {"timestamp_col": "ds", "target_col": "y", "frequency": "D"}

    model.fit(dataset, y_dataset, temporal_metadata=temporal_metadata)

    # Test 1: predict with periods (new standard)
    try:
        pred = model.predict(periods=5)
        print(f"✅ predict(periods=5) successful. Shape: {pred.shape}")
    except Exception as e:
        print(f"❌ predict(periods=5) failed: {e}")

    # Test 2: predict with horizon (backward compatibility)
    try:
        pred = model.predict(horizon=5)
        print(f"✅ predict(horizon=5) successful (compat). Shape: {pred.shape}")
    except Exception as e:
        print(f"❌ predict(horizon=5) failed: {e}")


if __name__ == "__main__":
    try:
        test_sklearn_forecaster()
        test_prophet_model()
        print("\nAll tests completed.")
    except Exception as e:
        print(f"\nGlobal error: {e}")
