"""DashAI RoC AUC classification metric implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ROCAUC(ClassificationMetric):
    """RoC AUC score to classification tasks."""

    DESCRIPTION: str = (
        "The Receiver Operating Characteristic Area Under the Curve (RoC AUC) "
        "is a performance measurement for classification problems at various "
        "threshold settings. It represents the degree or measure "
        "of separability between classes."
    )

    @staticmethod
    def score(
        true_labels: "DashAIDataset", probs_pred_labels, multiclass=None
    ) -> float:
        """Calculate RoC AUC score between true labels and predicted labels.

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
            RoC AUC score between true labels and predicted labels
        """
        true_labels, _ = prepare_to_metric(true_labels, probs_pred_labels)
        # Use the provided multiclass parameter or determine it using is_multiclass
        if multiclass is None:
            multiclass = ClassificationMetric.is_multiclass(true_labels)

        from sklearn.metrics import roc_auc_score

        if multiclass:
            return roc_auc_score(true_labels, probs_pred_labels, multi_class="ovr")
        else:
            return roc_auc_score(true_labels, probs_pred_labels[:, 1])
