"""DashAI RMSE regression metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RMSE(RegressionMetric):
    """Square root of the mean squared error between predicted and true values.

    Root Mean Squared Error (RMSE) is the square root of MSE, bringing the
    metric back to the same unit as the target variable. Like MSE, it
    penalises large errors more heavily than MAE, but its interpretability
    advantage over MSE makes it the standard regression error metric in most
    applications. RMSE is equivalent to the Euclidean distance between the
    prediction vector and the true value vector, normalised by sample count.

    .. math::

        \\text{RMSE}(y, \\hat{y}) = \\sqrt{\\frac{1}{N} \\sum_{i=1}^{N} (y_i - \\hat{y}_i)^2}

    Range: [0, +∞), lower is better (``MAXIMIZE = False``).

    References
    ----------
    .. [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html
    """

    DESCRIPTION: str = (
        "Square root of the average of squared differences between "
        "predicted and actual values, penalizes larger errors more heavily."
    )

    @staticmethod
    def score(true_values: "DashAIDataset", predicted_values) -> float:
        """Calculate the RMSE between true values and predicted values.

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
            RMSE score between true values and predicted values
        """
        from sklearn.metrics import root_mean_squared_error

        true_values, pred_values = prepare_to_metric(true_values, predicted_values)
        return root_mean_squared_error(true_values, pred_values)
