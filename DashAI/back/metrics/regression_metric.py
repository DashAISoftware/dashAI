from typing import Tuple

import numpy as np

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.base_metric import BaseMetric


class RegressionMetric(BaseMetric):
    """Class for metrics associated with regression models."""

    COMPATIBLE_COMPONENTS = ["RegressionTask"]


def validate_inputs(true_values: np.ndarray, pred_values: np.ndarray) -> None:
    """Validate inputs.

    Parameters
    ----------
    true_values : ndarray
        True values. Can be 1D (single-output) or 2D (multi-output).
    pred_values : ndarray
        Predicted values by the model. Can be 1D (single-output) or 2D (multi-output).
    """
    if len(true_values) != len(pred_values):
        raise ValueError(
            "The number of samples in true and predicted values must be equal, "
            f"given: len(true_values) = {len(true_values)} and "
            f"len(pred_values) = {len(pred_values)}."
        )

    # Additional validation for multi-output: check shape compatibility
    if (
        true_values.ndim > 1
        and pred_values.ndim > 1
        and true_values.shape[1] != pred_values.shape[1]
    ):
        raise ValueError(
            "The number of outputs in true and predicted values must be equal, "
            f"given: true_values.shape = {true_values.shape} and "
            f"pred_values.shape = {pred_values.shape}."
        )


def prepare_to_metric(
    y: DashAIDataset, predicted_values: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare true and predicted values to be used later in metrics.

    Parameters
    ----------
    y : DashAIDataset
        A DashAIDataset with the output columns of the data.
    predicted_values: np.ndarray
        Array with the predicted values for each instance. Can be 1D for single-output
        or 2D for multi-output regression.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        A tuple with the true and predicted values in numpy format.
    """
    # Handle multi-output regression: if we have multiple output columns,
    # convert all of them to a 2D array
    if len(y.column_names) > 1:
        # Multi-output case: combine all output columns into 2D array
        true_values_list = []
        for column_name in y.column_names:
            true_values_list.append(np.array(y[column_name]))
        true_values = np.column_stack(true_values_list)
        print(
            f"[prepare_to_metric] Multi-output: {len(y.column_names)} "
            f"columns -> shape {true_values.shape}"
        )
    else:
        # Single-output case: use the original behavior
        column_name = y.column_names[0]
        true_values = np.array(y[column_name])
        print(
            f"[prepare_to_metric] Single-output: 1 column -> shape {true_values.shape}"
        )

    # Ensure predicted_values has compatible shape
    if predicted_values.ndim == 1 and len(y.column_names) > 1:
        predicted_values = predicted_values.reshape(-1, 1)

    print(
        f"[prepare_to_metric] Final shapes - true: {true_values.shape}, "
        f"pred: {predicted_values.shape}"
    )

    # Filter out NaN values (common in forecasting with lag features)
    # For single-output: filter where either true or pred is NaN
    # For multi-output: filter rows where ANY value is NaN
    if predicted_values.ndim == 1 or len(y.column_names) == 1:
        # Single-output case
        valid_mask = ~(np.isnan(true_values) | np.isnan(predicted_values))
        n_nan = np.sum(~valid_mask)
        if n_nan > 0:
            print(f"[prepare_to_metric] Filtering {n_nan} NaN values")
            true_values = true_values[valid_mask]
            predicted_values = predicted_values[valid_mask]
    else:
        # Multi-output case: filter rows with ANY NaN
        valid_mask = ~(
            np.isnan(true_values).any(axis=1) | np.isnan(predicted_values).any(axis=1)
        )
        n_nan = np.sum(~valid_mask)
        if n_nan > 0:
            print(f"[prepare_to_metric] Filtering {n_nan} rows with NaN values")
            true_values = true_values[valid_mask]
            predicted_values = predicted_values[valid_mask]

    if len(true_values) == 0:
        raise ValueError("All values are NaN after filtering. Cannot compute metrics.")

    validate_inputs(true_values, predicted_values)
    return true_values, predicted_values
