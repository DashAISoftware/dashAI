"""Symmetric Mean Absolute Percentage Error (sMAPE) metric for forecasting."""

import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric


class SMAPE(RegressionMetric):
    """Symmetric Mean Absolute Percentage Error metric for forecasting tasks.

    sMAPE is a more stable version of MAPE that handles zero values better
    by using the average of actual and predicted values in the denominator.

    sMAPE = (2/n) * Σ|(y_true - y_pred)| / (|y_true| + |y_pred|) * 100

    sMAPE is bounded between 0% and 200%, making it more stable than MAPE.
    """

    COMPATIBLE_COMPONENTS = [
        "RegressionTask",
        "MultiOutputRegressionTask",
        "ForecastingTask",
    ]

    @staticmethod
    def score(true_values: DashAIDataset, predicted_values: np.ndarray) -> float:
        """Calculate sMAPE between true values and predicted values.

        Parameters
        ----------
        true_values : DashAIDataset
            A DashAI dataset with true values.
        predicted_values : np.ndarray
            Array with the predicted values for each instance.

        Returns
        -------
        float
            sMAPE score as percentage (0-200, lower is better)
        """
        true_values, pred_values = prepare_to_metric(true_values, predicted_values)

        # Calculate symmetric denominator
        denominator = np.abs(true_values) + np.abs(pred_values)

        # Handle zero denominator (both actual and predicted are zero)
        mask = denominator > 1e-8

        if not np.any(mask):
            # All values are essentially zero
            return 0.0

        # Calculate sMAPE
        smape_values = np.abs(true_values[mask] - pred_values[mask]) / denominator[mask]

        return float(np.mean(smape_values) * 200)
