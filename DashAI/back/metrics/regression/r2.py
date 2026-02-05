"""DashAI R2 score implementation."""

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric


class R2(RegressionMetric):
    """R2 score metric for regression tasks."""

    MAXIMIZE: bool = True
    DESCRIPTION: str = (
        "R2 score, also known as the coefficient of determination, "
        "measures how well the predicted values from a regression model "
        "approximate the actual data points. It provides an indication of "
        "the goodness of fit of the model."
    )

    @staticmethod
    def score(true_values: DashAIDataset, pred_values) -> float:
        """Calculate the R2 score between true values and predicted values.

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
            R2 score between true values and predicted values
        """
        from sklearn.metrics import r2_score

        true_values, pred_values = prepare_to_metric(true_values, pred_values)
        return r2_score(true_values, pred_values)
