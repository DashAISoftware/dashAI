"""DashAI recall classification metric implementation."""

import numpy as np
from sklearn.metrics import recall_score

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)


class Recall(ClassificationMetric):
    """Recall metric to classification tasks."""

    @staticmethod
    def score(
        true_labels: DashAIDataset, probs_pred_labels: np.ndarray, multiclass=None
    ) -> float:
        """Calculate recall between true labels and predicted labels.

        Parameters
        ----------
        true_labels : DashAIDataset
            A DashAI dataset with labels.
        probs_pred_labels : np.ndarray
            A two-dimensional matrix in which each column represents a class and the row
            values represent the probability that an example belongs to the class
            associated with the column.
        multiclass : bool, optional
            Whether the task is a multiclass classification. If None, it will be
            determined automatically from the number of unique labels.

        Returns
        -------
        float
            recall score between true labels and predicted labels
        """
        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)

        # Use the provided multiclass parameter or determine it using is_multiclass
        if multiclass is None:
            multiclass = ClassificationMetric.is_multiclass(true_labels)

        if multiclass:
            return recall_score(true_labels, pred_labels, average="macro")
        else:
            return recall_score(true_labels, pred_labels, average="binary")
