"""DashAI R2 score implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.regression_metric import RegressionMetric, prepare_to_metric

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class R2(RegressionMetric):
    """Coefficient of determination — goodness of fit for regression models.

    R² (R-squared) measures the proportion of variance in the target variable
    that is explained by the model. It compares the model's predictions to a
    trivial baseline that always predicts the target mean. An R² of 1.0 means
    the model explains all variance perfectly; 0.0 means it is no better than
    the mean predictor; negative values indicate worse-than-baseline performance.

    R² is scale-invariant (unlike MAE/MSE), making it easy to compare models
    trained on targets with different units or magnitudes.

    .. math::

        R^2(y, \\hat{y}) = 1 - \\frac{\\sum_{i}(y_i - \\hat{y}_i)^2}{\\sum_{i}(y_i - \\bar{y})^2}

    Range: (−∞, 1], higher is better (``MAXIMIZE = True``).

    References
    ----------
    .. [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html
    """

    MAXIMIZE: bool = True
    DESCRIPTION: str = (
        "R2 score, also known as the coefficient of determination, "
        "measures how well the predicted values from a regression model "
        "approximate the actual data points. It provides an indication of "
        "the goodness of fit of the model."
    )

    @staticmethod
    def score(true_values: "DashAIDataset", pred_values) -> float:
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
