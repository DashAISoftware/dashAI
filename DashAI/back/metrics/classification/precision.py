"""DashAI precision classification metric implementation."""

from typing import TYPE_CHECKING, Optional

from DashAI.back.core.utils import MultilingualString
from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Precision(ClassificationMetric):
    """Fraction of positive predictions that are actually correct.

    Precision (also called positive predictive value) measures the ability
    of the classifier to avoid labelling negative samples as positive. It is
    the metric of choice when the cost of false positives is high — e.g. in
    spam detection, flagging a legitimate email is more costly than missing
    a spam.

    For binary tasks the standard binary precision is used. For multiclass
    tasks, macro averaging (unweighted mean over all classes) is applied.

    ::

        Precision = TP / (TP + FP)

    Range: [0, 1], higher is better (``MAXIMIZE = True``).

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html
    """

    DESCRIPTION = MultilingualString(
        en=(
            "Fraction of predicted positives that are correct, "
            "important when false positives are costly."
        ),
        es=(
            "Fracción de positivos predichos que son correctos, "
            "importante cuando los falsos positivos son costosos."
        ),
        pt=(
            "Fração dos positivos previstos que estão corretos, "
            "importante quando os falsos positivos são custosos."
        ),
        de=(
            "Anteil der vorhergesagten Positiven, die korrekt sind, "
            "wichtig wenn falsch-positive Ergebnisse kostspielig sind."
        ),
    )

    @staticmethod
    def score(
        true_labels: "DashAIDataset",
        probs_pred_labels: "np.ndarray",
        multiclass: Optional[bool] = None,
    ) -> float:
        """Calculate precision between true labels and predicted labels.

        Parameters
        ----------
        true_labels : DashAIDataset
            A DashAI dataset with labels.
        probs_pred_labels : np.ndarray
            A two-dimensional matrix in which each column represents a class
            and the row values represent the probability that an example belongs
            to the class associated with the column.
        multiclass : bool, optional
            Whether the task is a multiclass classification. If None, it will be
            determined automatically from the number of unique labels.

        Returns
        -------
        float
            Precision score between true labels and predicted labels
        """
        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)

        # Use the provided multiclass parameter or determine it using is_multiclass
        if multiclass is None:
            multiclass = ClassificationMetric.is_multiclass(true_labels)

        from sklearn.metrics import precision_score

        if multiclass:
            return precision_score(true_labels, pred_labels, average="macro")
        else:
            return precision_score(true_labels, pred_labels, average="binary")
