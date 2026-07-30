"""Base Diagnostic abstract class."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final, List, Optional, Union

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.artifacts import Artifact, GroupedArtifacts

if TYPE_CHECKING:
    from numpy import ndarray


class DiagnosticError(Exception):
    """Raised when a diagnostic cannot be computed from the inputs it got."""


class BaseDiagnostic(ConfigObject, ABC):
    """Abstract base class for evaluation diagnostics.

    A diagnostic is the artifact-valued sibling of a metric. Both are computed
    from the same inputs at the same moment, comparing a model's predictions
    over a split against the truth; they differ only in codomain::

        Metric:     (y_true, y_pred) -> float      (rankable, optimizable)
        Diagnostic: (y_true, y_pred) -> artifact   (structured, not rankable)

    That is why a confusion matrix or an ROC curve cannot be a ``Metric``: a
    K x K grid does not fit a float column, cannot be ranked for model
    selection and cannot be handed to a hyperparameter optimizer. The scalar
    summaries of those shapes (accuracy, ROC AUC) already exist as metrics; a
    diagnostic renders the shape those numbers condense.

    A diagnostic is also not an explainer. An explainer probes how the model
    responds to *features*; a diagnostic never looks at the inputs at all, only
    at predictions against the truth.

    Class attributes
    ----------------
    TYPE : str
        Always ``"Diagnostic"``; used by the DashAI component registry.
    REQUIRES_PROBABILITIES : bool
        ``True`` when ``compute`` needs the full class probability matrix
        rather than hard labels. The job checks the actual prediction shape
        against this before running, so an incompatible model fails with a
        clear message instead of a shape error deep inside a plot call.
    DISPLAY_NAME, DESCRIPTION, COLOR, ICON
        UI metadata, matching the conventions used by models and explainers.
    """

    TYPE: Final[str] = "Diagnostic"
    REQUIRES_PROBABILITIES: bool = False
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    COLOR: str = "#5C6BC0"
    ICON: str = "Insights"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current diagnostic.

        Returns
        -------
        Dict[str, Any]
            UI metadata, including whether the diagnostic needs a model that
            outputs class probabilities.
        """
        metadata: Dict[str, Any] = {}
        metadata["icon"] = cls.ICON if cls.ICON else "Insights"
        metadata["requires_probabilities"] = cls.REQUIRES_PROBABILITIES
        return metadata

    @abstractmethod
    def compute(
        self,
        y_true: "ndarray",
        y_pred: "ndarray",
        class_names: Optional[List[str]] = None,
    ) -> List[Union[Artifact, GroupedArtifacts]]:
        """Build renderable artifacts comparing predictions against the truth.

        Parameters
        ----------
        y_true : ndarray
            Ground truth for the split, encoded the way the model was trained:
            class indexes for classification, raw values for regression.
        y_pred : ndarray
            What the model's ``predict`` returned for the same rows. DashAI
            classifiers return a ``(n_samples, n_classes)`` probability matrix
            and regressors return a 1D array of values, so a diagnostic that
            needs hard labels takes the argmax itself.
        class_names : Optional[List[str]]
            Class labels in encoded order, or None for regression.

        Returns
        -------
        List[Union[Artifact, GroupedArtifacts]]
            The artifacts to render, in display order.

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError


def as_labels(y_pred: "ndarray") -> "ndarray":
    """Reduce a prediction array to hard class labels.

    Parameters
    ----------
    y_pred : ndarray
        Either a ``(n_samples, n_classes)`` probability matrix or a 1D array of
        labels.

    Returns
    -------
    ndarray
        A 1D array of class indexes.
    """
    import numpy as np

    predictions = np.asarray(y_pred)
    return predictions.argmax(axis=1) if predictions.ndim == 2 else predictions


def resolve_class_names(class_names: Optional[List[str]], n_classes: int) -> List[str]:
    """Fill in class labels when the run carries none.

    Parameters
    ----------
    class_names : Optional[List[str]]
        Labels in encoded order, possibly None or shorter than ``n_classes``.
    n_classes : int
        How many classes the model predicts.

    Returns
    -------
    List[str]
        Exactly ``n_classes`` labels, falling back to the class index.
    """
    names = list(class_names or [])
    return [
        str(names[index]) if index < len(names) else str(index)
        for index in range(n_classes)
    ]
