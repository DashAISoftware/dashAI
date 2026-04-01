"""DashAI accuracy classification metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Accuracy(ClassificationMetric):
    """Fraction of correctly classified samples over all predictions.

    Accuracy is the simplest classification metric: the number of correct
    predictions divided by the total number of samples. It is well-suited
    for balanced datasets but can be misleading when class distributions are
    skewed — a model that always predicts the majority class would still
    score high without learning anything useful.

    .. math::

        \\text{Accuracy} = \\frac{\\text{correct predictions}}{\\text{total samples}}

    Range: [0, 1], higher is better (``MAXIMIZE = True``).

    References
    ----------
    .. [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html
    """

    DESCRIPTION: str = (
        "Proportion of correct predictions over all samples, "
        "best suited for balanced datasets."
    )

    @staticmethod
    def score(true_labels: "DashAIDataset", probs_pred_labels) -> float:
        """Calculate the accuracy between true labels and predicted labels.

        Parameters
        ----------
        true_labels : DashAIDataset
            A DashAI dataset with labels.
        probs_pred_labels : np.ndarray
            A two-dimensional matrix in which each column represents a class
            and the row values represent the probability that an example belongs
            to the class associated with the column.

        Returns
        -------
        float
            Accuracy score between true labels and predicted labels
        """
        from sklearn.metrics import accuracy_score

        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)
        return accuracy_score(true_labels, pred_labels)
