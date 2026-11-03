from typing import TYPE_CHECKING

from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.metrics.forecasting_metric import PointMetricMixin

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RegressionMetric(PointMetricMixin, BaseMetric):
    """Base class for all regression evaluation metrics.

    Subclasses implement :meth:`score` to quantify the difference between
    continuous predicted values and ground-truth targets. By default
    regression metrics are minimised (``MAXIMIZE = False``) because smaller
    error values indicate better performance.

    Compatible with DashAI regression tasks. The helper ``prepare_to_metric``
    in this module converts ``DashAIDataset`` targets and raw numpy predictions
    to flat numpy arrays before passing them to sklearn metric functions.

    A forecast is scored through ``score_forecast`` (``PointMetricMixin``),
    which hands its actual values and point forecast to the same ``score``.
    """

    MAXIMIZE: bool = False
    # Only regression. A forecasting task that shares one of these metrics
    # lists it in its own COMPATIBLE_COMPONENTS, as SingleSeriesForecastingTask
    # does with MAE and RMSE, so the metric never names a forecasting task.
    COMPATIBLE_COMPONENTS = ["RegressionTask"]


def prepare_to_metric(
    y: "DashAIDataset",
    y_pred: "np.ndarray",
) -> tuple["np.ndarray", "np.ndarray"]:
    """
    Prepare true and predicted values for metric calculation.

    Parameters
    ----------
    y : DashAIDataset or array-like
        True values. A forecast is scored against the actual values of the
        series as an array, a run against the target column as a dataset.
    y_pred : np.ndarray
        Predicted values by the model.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Tuple containing true values and predicted values as numpy arrays.
    """
    import numpy as np

    values = y.to_pandas().to_numpy() if hasattr(y, "to_pandas") else np.asarray(y)
    true_values = np.array(values, dtype=float).flatten()
    pred_values = np.array(y_pred).flatten()

    return true_values, pred_values
