"""DashAI Hamming Distance implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class HammingDistance(ClassificationMetric):
    """Fraction of labels that are incorrectly predicted (Hamming loss).

    The Hamming distance (or Hamming loss) is the fraction of the total
    predictions that are wrong. For single-label classification it equals
    ``1 − accuracy``; for multi-label classification it counts per-label
    mismatches independently, making it especially useful when each sample
    can belong to multiple classes simultaneously.

    A lower Hamming distance indicates better performance. ``MAXIMIZE = False``
    so the DashAI framework treats smaller values as improvements.

    .. math::

        \\text{Hamming Loss} = \\frac{1}{N} \\sum_{i=1}^{N} \\mathbb{1}[\\hat{y}_i \\neq y_i]

    Range: [0, 1], lower is better (``MAXIMIZE = False``).

    References
    ----------
    .. [1] Hamming, R.W. (1950). "Error detecting and error correcting codes."
           Bell System Technical Journal, 29(2), 147–160.
    .. [2] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.hamming_loss.html
    """

    MAXIMIZE: bool = False
    DESCRIPTION: str = (
        "Hamming Distance measures the fraction of "
        "labels that are incorrectly predicted. "
        "It is particularly useful for multi-label classification tasks."
    )

    @staticmethod
    def score(
        true_labels: "DashAIDataset", probs_pred_labels, multiclass=None
    ) -> float:
        """Calculate Hamming Distance between true labels and predicted labels.

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
            Hamming Distance between true labels and predicted labels
        """
        from sklearn.metrics import hamming_loss

        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)
        return hamming_loss(true_labels, pred_labels)
