"""Base Metric abstract class."""

from typing import TYPE_CHECKING, Any, Dict, Final, Tuple, Union

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseMetric:
    """Abstract class of all metrics.

    Attributes
    ----------
    HIGHER_IS_BETTER : bool
        Indicates the optimization direction for this metric.
        - True: Higher values are better (e.g., Accuracy, F1)
        - False: Lower values are better (e.g., MAE, RMSE, SMAPE)

        This attribute is used by hyperparameter optimizers to determine
        whether to maximize or minimize the metric during optimization.
    """

    TYPE: Final[str] = "Metric"
    MAXIMIZE: Final[bool] = False
    metadata: Dict[str, Any] = {}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get metadata values for the current metric.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata
        """
        meta: Dict[str, Any] = dict(getattr(cls, "metadata", {}) or {})
        meta["maximize"] = cls.MAXIMIZE

        return meta


METRICS_MAP = {
    "classification": ["Accuracy", "F1", "Precision", "Recall"],
    "regression": ["RMSE", "MAE"],
    "translation": ["Bleu", "Ter"],
}


def validate_inputs(
    true: Union["ndarray", list], pred: Union["ndarray", list], metric_category: str
) -> None:
    """Validate inputs.

    Parameters
    ----------
    true: ndarray, list
        True labels.
    pred: nndarray, list
        Predicted labels by the model.
    metric_category: str
        The name of the category of metric to be used as base to validate the labels.

    """

    if len(true) != len(pred):
        if metric_category in ["classification", "translation"]:
            raise ValueError(
                "The length of the true labels and the predicted labels must be equal, "
                f"given: len(true_labels) = {len(true)} and "
                f"len(pred_labels) = {len(pred)}."
            )
        elif metric_category in ["regression"]:
            raise ValueError(
                "The length of the true and the predicted values must be equal, "
                f"given: len(true_values) = {len(true)} and "
                f"len(pred_values) = {len(pred)}."
            )


def prepare_to_metric(
    y: "DashAIDataset",
    pre_pred: Union["ndarray", list],
    metric_type: str,
) -> Tuple["ndarray", Union["ndarray", list]]:
    """Prepare true and prediced labels to be used later in metrics.

    Parameters
    ----------
    y : DashAIDataset
        A DashAIDataset with the output columns of the data.
    probs_pred_labels : np.ndarray
        A two-dimensional matrix in which each column represents a class and the row
        values represent the probability that an example belongs to the class
        associated with the column.
    metric_type : str
        The name of the kind of metric to be used and how to prepare the labels.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        A tuple with the true and predicted labels in numpy format.
    """
    import numpy as np

    column_name = y.column_names[0]
    _pred = None
    _true = None

    for metric_category, metrics in METRICS_MAP.items():
        if metric_type in metrics:
            if metric_category == "classification":
                if not isinstance(pre_pred, np.ndarray):
                    raise TypeError(
                        f"Expected np.ndarray for regression, got {type(pre_pred)}"
                    )
                _true = np.array(y[column_name])
                validate_inputs(_true, pre_pred, metric_category)
                _pred = np.argmax(pre_pred, axis=1)

            elif metric_category == "regression":
                if not isinstance(pre_pred, np.ndarray):
                    raise TypeError(
                        f"Expected np.ndarray for regression, got {type(pre_pred)}"
                    )
                _true = np.array(y[column_name])
                validate_inputs(_true, pre_pred, metric_category)
                _pred = pre_pred

            elif metric_category == "translation":
                if not isinstance(pre_pred, list):
                    raise TypeError(
                        f"Expected list for translation, got {type(pre_pred)}"
                    )
                _true = np.array(y[column_name])
                validate_inputs(_true, pre_pred, metric_category)
                _pred = pre_pred
            else:
                raise ValueError(f"Unsupported metric type: {metric_type}")

    return _true, _pred
