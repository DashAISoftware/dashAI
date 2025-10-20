"""Mean Absolute Percentage Error (MAPE) metric for forecasting."""

import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric


class MAPE(RegressionMetric):
    """Mean Absolute Percentage Error metric for forecasting tasks.

    MAPE measures the average absolute percentage difference between
    predicted and actual values. It's scale-independent and easy to interpret.

    MAPE = (1/n) * Σ|((y_true - y_pred) / y_true)| * 100

    Note: MAPE can be problematic when true values are close to zero.
    """

    COMPATIBLE_COMPONENTS = [
        "RegressionTask",
        "MultiOutputRegressionTask",
        "ForecastingTask",
    ]

    @staticmethod
    def score(true_values: DashAIDataset, predicted_values: np.ndarray) -> float:
        """Calculate MAPE between true values and predicted values.

        Parameters
        ----------
        true_values : DashAIDataset
            A DashAI dataset with true values.
        predicted_values : np.ndarray
            Array with the predicted values for each instance.

        Returns
        -------
        float
            MAPE score as percentage (0-100, lower is better)
        """
        true_values, pred_values = prepare_to_metric(true_values, predicted_values)

        # Handle zero values in denominator
        mask = np.abs(true_values) > 1e-8  # Avoid division by very small numbers

        if not np.any(mask):
            # All true values are essentially zero
            return 0.0 if np.allclose(pred_values, 0) else 100.0

        # Calculate MAPE only for non-zero true values
        mape_values = np.abs(
            (true_values[mask] - pred_values[mask]) / true_values[mask]
        )

        return float(np.mean(mape_values) * 100)
