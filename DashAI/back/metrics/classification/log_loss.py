"""DashAI log loss implementation."""

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)


class LogLoss(ClassificationMetric):
    """Log Loss score for classification tasks."""

    DESCRIPTION: str = (
        "Log Loss, also known as Logistic Loss or Cross-Entropy Loss, "
        "measures the performance of a classification model "
        "where the prediction input is a probability value "
        "between 0 and 1."
    )

    MAXIMIZE: bool = False

    @staticmethod
    def score(true_labels: DashAIDataset, probs_pred_labels, multiclass=None) -> float:
        """Calculate Log Loss score between true labels and predicted labels.

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
            Log Loss score between true labels and predicted labels
        """
        from sklearn.metrics import log_loss

        true_labels, _ = prepare_to_metric(true_labels, probs_pred_labels)

        return log_loss(true_labels, probs_pred_labels)
