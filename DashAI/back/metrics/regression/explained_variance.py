"""DashAI Explained Variance regression metric implementation."""

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric


class ExplainedVariance(RegressionMetric):
    """Explained Variance metric for regression tasks."""

    DESCRIPTION: str = (
        "Explained Variance measures the proportion of the variance in the "
        "dependent variable that is predictable from the independent variables "
        "in a regression model. It provides an indication of how well the model "
        "captures the variability of the data."
    )

    @staticmethod
    def score(true_values: DashAIDataset, predicted_values) -> float:
        """Calculate the Explained Variance between true values and predicted values.

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
            Explained Variance score between true values and predicted values
        """
        from sklearn.metrics import explained_variance_score

        true_values, pred_values = prepare_to_metric(true_values, predicted_values)
        return explained_variance_score(true_values, pred_values)
