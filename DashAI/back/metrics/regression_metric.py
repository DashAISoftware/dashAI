from typing import TYPE_CHECKING

from DashAI.back.metrics.base_metric import BaseMetric

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RegressionMetric(BaseMetric):
    """Class for metrics associated with regression models."""

    MAXIMIZE: bool = False
    COMPATIBLE_COMPONENTS = ["RegressionTask"]


def prepare_to_metric(
    y: "DashAIDataset",
    y_pred: "ndarray",
) -> tuple["ndarray", "ndarray"]:
    """
    Prepare true and predicted values for metric calculation.

    Parameters
    ----------
    y : DashAIDataset
        True values.
    y_pred : np.ndarray
        Predicted values by the model.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Tuple containing true values and predicted values as numpy arrays.
    """
    import numpy as np

    true_values = np.array(y.to_pandas().to_numpy().flatten())
    pred_values = np.array(y_pred).flatten()

    return true_values, pred_values
