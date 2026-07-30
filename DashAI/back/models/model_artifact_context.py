"""Naming handed to a model's ``get_model_artifacts`` hook."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ModelArtifactContext:
    """Labels needed to render a fitted model's own parameters.

    Deliberately carries no training data. A model visualization is computable
    from the fitted model alone; anything that needs a feature range to sweep
    or a prediction set to compare against belongs to a global explainer or a
    metric respectively. The names here exist only because an estimator stores
    column positions rather than column labels, so the labels have to be
    supplied from outside.

    The names are in the model's own feature space, that is, after
    ``prepare_dataset`` has run, so they line up with the columns the fitted
    estimator actually split on.

    Attributes
    ----------
    feature_names : List[str]
        Input feature names in the model's feature space.
    class_names : Optional[List[str]]
        Class labels in encoded order, or None for regressors.
    """

    feature_names: List[str]
    class_names: Optional[List[str]] = None
