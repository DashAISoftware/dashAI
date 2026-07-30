"""Data handed to a model's ``get_model_artifacts`` hook."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd


@dataclass
class ModelArtifactContext:
    """Training data and naming needed to visualise a fitted model.

    The frame is expressed in the model's own feature space, that is, after
    ``prepare_dataset`` has run, so ``feature_names`` line up with the columns
    the fitted estimator actually split on.

    Attributes
    ----------
    x_train : pd.DataFrame
        Training features in the model's feature space.
    y_train : np.ndarray
        Training targets, encoded through ``prepare_output``.
    feature_names : List[str]
        Column names of ``x_train``.
    class_names : Optional[List[str]]
        Class labels in encoded order, or None for regressors.
    """

    x_train: "pd.DataFrame"
    y_train: "np.ndarray"
    feature_names: List[str]
    class_names: Optional[List[str]] = None
