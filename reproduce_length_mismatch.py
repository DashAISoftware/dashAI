import numpy as np
import pandas as pd

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.explainability.explainers.forecasting_explainers import (
    forecast_decomposition,
)
from DashAI.back.models.forecasting.sklearn_multistep_forecaster import (
    SklearnMultiStepForecaster,
)


def create_dummy_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    values = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    data = pd.DataFrame({"ds": dates, "y": values})
    return to_dashai_dataset(data)


def reproduce_error():
    print("\nReproducing length mismatch error...")
    dataset = create_dummy_data()

    # Create x (features) and y (target) datasets
    x_df = dataset.to_pandas()
    y_df = x_df[["y"]]
    y_dataset = to_dashai_dataset(y_df)

    # Train with default horizon (which is 1 usually, or from fit_params)
    # If we don't specify horizon, it defaults to 1 in SklearnMultiStepForecaster
    model = SklearnMultiStepForecaster(window_size=5, forecast_strategy="direct")

    temporal_metadata = {"timestamp_col": "ds", "target_col": "y", "frequency": "D"}

    print("Training model (default horizon=1)...")
    model.fit(dataset, y_dataset, temporal_metadata=temporal_metadata)

    # Create a dataset that extends beyond the training data
    # Training was 100 days from 2023-01-01 (ends ~2023-04-10)
    # Let's create a "validation" dataset that goes up to 2023-06-01
    dates_extended = pd.date_range(start="2023-01-01", end="2023-06-01", freq="D")
    values_extended = np.sin(
        np.linspace(0, 15, len(dates_extended))
    ) + np.random.normal(0, 0.1, len(dates_extended))
    df_extended = pd.DataFrame({"ds": dates_extended, "y": values_extended})
    dataset_extended = to_dashai_dataset(df_extended)

    # Create x (features) and y (target) datasets for extended data
    x_df_ext = dataset_extended.to_pandas()
    y_df_ext = x_df_ext[["y"]]
    y_dataset_ext = to_dashai_dataset(y_df_ext)

    print(f"Extended dataset ends at: {dates_extended.max()}")

    # Now try to explain with horizon 30 using the EXTENDED dataset
    print("Attempting explain with horizon=30 using extended dataset...")
    explainer = forecast_decomposition.ForecastDecomposition(model, horizon=30)

    try:
        # explain() needs a dataset tuple (x, y)
        explanation = explainer.explain((dataset_extended, y_dataset_ext))
        print("✅ Explanation successful!")
        print(f"Explanation keys: {explanation.keys()}")
        print(f"Explanation ds length: {len(explanation['ds'])}")
        ds_series = pd.Series(explanation["ds"])
        print(f"Explanation start date: {ds_series.min()}")
        print(f"Explanation end date: {ds_series.max()}")

        # Verify start date is after extended dataset
        expected_start = dates_extended.max() + pd.Timedelta(days=1)
        if ds_series.min() == expected_start:
            print("✅ Start date matches expected (from extended dataset)")
        else:
            print(
                f"❌ Start mismatch! Expected {expected_start}, got {ds_series.min()}"
            )

    except Exception as e:
        print(f"❌ Explanation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce_error()
