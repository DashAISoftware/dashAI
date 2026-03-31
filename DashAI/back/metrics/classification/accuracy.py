"""DashAI accuracy classification metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Accuracy(ClassificationMetric):
    """Accuracy metric to classification tasks.

    Higher accuracy values are better (range: 0.0 to 1.0).
    """

    HIGHER_IS_BETTER = True

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
