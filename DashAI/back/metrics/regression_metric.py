import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.base_metric import BaseMetric


class RegressionMetric(BaseMetric):
    """Class for metrics associated with regression models."""

    MAXIMIZE: bool = False
    COMPATIBLE_COMPONENTS = ["RegressionTask"]


def prepare_to_metric(
    y: DashAIDataset,
    y_pred: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
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
    # Handle both DashAIDataset and numpy array inputs
    if isinstance(y, np.ndarray):
        true_values = np.array(y).flatten()
    else:
        true_values = np.array(y.to_pandas().to_numpy().flatten())
    pred_values = np.array(y_pred).flatten()

    return true_values, pred_values
