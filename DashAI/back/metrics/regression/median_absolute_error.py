"""Median Absolute Error metric for regression tasks."""

import numpy as np
from sklearn.metrics import median_absolute_error

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric


class MedianAbsoluteError(RegressionMetric):
    """Median Absolute Error metric for regression tasks."""

    DESCRIPTION: str = (
        "Median Absolute Error (MedAE) measures the median "
        "of the absolute differences "
        "between predicted values and actual values in a regression model. "
        "It provides a robust measure of prediction accuracy, "
        "less sensitive to outliers "
        "compared to Mean Absolute Error (MAE)."
    )

    @staticmethod
    def score(true_values: DashAIDataset, predicted_values: np.ndarray) -> float:
        """Calculate the Median Absolute Error between true values and predicted values.

        Parameters
        ----------
        true_values : DashAIDataset
            A DashAI dataset with true values.
        predicted_values : np.ndarray
            A one-dimensional array with the predicted values
            for each instance.

        Returns
        -------
        float
            Median Absolute Error score between true values and predicted values
        """
        true_values, pred_values = prepare_to_metric(true_values, predicted_values)
        return median_absolute_error(true_values, pred_values)
