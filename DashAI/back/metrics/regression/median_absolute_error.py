"""Median Absolute Error metric for regression tasks."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class MedianAbsoluteError(RegressionMetric):
    """Median of absolute differences between predicted and true values.

    Median Absolute Error (MedAE) is a robust regression metric that uses the
    median rather than the mean of the absolute residuals. Because the median
    is insensitive to extreme values, MedAE is far less affected by outliers
    than MAE, MSE, or RMSE, making it the preferred metric when the target
    distribution has heavy tails or occasional extreme measurements.

    ::

        MedAE(y, ŷ) = median( |y₁ - ŷ₁|, …, |yₙ - ŷₙ| )

    Range: [0, +∞), lower is better (``MAXIMIZE = False``).

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.median_absolute_error.html
    """

    DESCRIPTION: str = (
        "Median Absolute Error (MedAE) measures the median "
        "of the absolute differences "
        "between predicted values and actual values in a regression model. "
        "It provides a robust measure of prediction accuracy, "
        "less sensitive to outliers "
        "compared to Mean Absolute Error (MAE)."
    )

    @staticmethod
    def score(
        true_values: "DashAIDataset",
        predicted_values: "np.ndarray",
    ) -> float:
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
        from sklearn.metrics import median_absolute_error

        true_values, pred_values = prepare_to_metric(true_values, predicted_values)
        return median_absolute_error(true_values, pred_values)
