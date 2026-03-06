from typing import TYPE_CHECKING

from DashAI.back.metrics.base_metric import BaseMetric

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TranslationMetric(BaseMetric):
    """Class for metrics associated to translation models."""

    COMPATIBLE_COMPONENTS = ["TranslationTask"]


def prepare_to_metric(
    y: "DashAIDataset",
    y_pred: "ndarray",
) -> tuple["ndarray", "ndarray"]:
    """Prepare data for metric calculation.

    Parameters
    ----------
    y : DashAIDataset
        True labels.
    y_pred : ndarray
        Predicted labels by the model.

    Returns
    -------
    tuple[ndarray, ndarray]
        Prepared true and predicted labels.

    Raises
    ------
    ValueError
        If the lengths of true and predicted labels do not match.
    """
    import numpy as np

    column_name = y.column_names[0]
    true = np.array(y[column_name])
    pred = y_pred

    return true, pred
