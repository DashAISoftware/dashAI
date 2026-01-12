"""DashAI Cohen Kappa classification metric implementation."""

import numpy as np
from sklearn.metrics import cohen_kappa_score

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)


class CohenKappa(ClassificationMetric):
    """Cohen Kappa score to classification tasks."""

    DESCRIPTION: str = (
        "Cohen Kappa score measures the agreement between two raters "
        "who each classify items into mutually exclusive categories."
    )

    @staticmethod
    def score(
        true_labels: DashAIDataset, probs_pred_labels: np.ndarray, multiclass=None
    ) -> float:
        """Calculate Cohen Kappa score between true labels and predicted labels.

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
            Cohen Kappa score between true labels and predicted labels
        """
        true_labels, pred_labels = prepare_to_metric(true_labels, probs_pred_labels)

        return cohen_kappa_score(true_labels, pred_labels)
