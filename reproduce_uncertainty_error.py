import numpy as np
import pandas as pd

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.explainability.explainers.forecasting_explainers import (
    forecast_uncertainty,
)
from DashAI.back.models.forecasting.sklearn_multistep_forecaster import (
    SklearnMultiStepForecaster,
)


def reproduce_error():
    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    values = np.sin(np.linspace(0, 10, 100)) + np.random.normal(0, 0.1, 100)
    data = pd.DataFrame({"ds": dates, "y": values})

    # Create DashAI datasets
    dataset = to_dashai_dataset(data)

    # Create x (features) and y (target) datasets
    # For this simple case, we'll just use the same dataset for both structure,
    # but in reality x would be features and y would be target
    x_df = data.drop(columns=["y"])
    y_df = data[["y"]]

    to_dashai_dataset(x_df)  # Not used directly, validation only
    y_dataset = to_dashai_dataset(y_df)

    # Initialize model
    model = SklearnMultiStepForecaster()

    # Fit model
    print("Training model...")
    temporal_metadata = {"timestamp_col": "ds", "target_col": "y", "frequency": "D"}
    model.fit(dataset, y_dataset, temporal_metadata=temporal_metadata)

    # Initialize explainer
    print("Initializing ForecastUncertainty explainer...")
    explainer = forecast_uncertainty.ForecastUncertainty(model, horizon=30)

    # Explain
    print("Attempting to explain...")
    try:
        explanation = explainer.explain((dataset, y_dataset))
        print("✅ Explanation successful!")
        print(f"Explanation keys: {explanation.keys()}")
        print(f"Explanation ds length: {len(explanation['ds'])}")
    except Exception as e:
        print(f"❌ Explanation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce_error()
