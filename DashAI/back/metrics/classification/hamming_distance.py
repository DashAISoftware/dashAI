"""DashAI Hamming Distance implementation."""

import numpy as np
from sklearn.metrics import hamming_loss

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)


class HammingDistance(ClassificationMetric):
    """Hamming Distance to classification tasks."""

    MAXIMIZE: bool = False
    DESCRIPTION: str = (
        "Hamming Distance measures the fraction of "
        "labels that are incorrectly predicted. "
        "It is particularly useful for multi-label classification tasks."
    )

    @staticmethod
    def score(
        true_labels: DashAIDataset, probs_pred_labels: np.ndarray, multiclass=None
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
        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)
        return hamming_loss(true_labels, pred_labels)
