"""DashAI RMSE regression metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RMSE(RegressionMetric):
    """Root Mean Squared Error metric for regression tasks."""

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
