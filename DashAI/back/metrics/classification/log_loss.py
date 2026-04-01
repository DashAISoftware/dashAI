"""DashAI log loss implementation."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.classification_metric import (
    ClassificationMetric,
    prepare_to_metric,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class LogLoss(ClassificationMetric):
    """
    Negative log-likelihood of true labels under the predicted probability distribution.

    Log Loss (cross-entropy loss) penalises confident wrong predictions much
    more heavily than uncertain ones. Unlike accuracy or F1, it evaluates the
    full probability output of the classifier rather than just the argmax
    label, rewarding well-calibrated models.

    Lower values indicate better performance (``MAXIMIZE = False``). A perfect
    classifier achieves log loss of 0; a random classifier on a binary problem
    achieves approximately ln(2) ≈ 0.693.

    ::

        Log Loss = -(1/N) · Σᵢ Σ_c yᵢ_c · log(pᵢ_c)

    where yᵢ_c is 1 if sample i belongs to class c and pᵢ_c is the
    predicted probability.

    Range: [0, +∞), lower is better (``MAXIMIZE = False``).

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html
    """

    DESCRIPTION: str = (
        "Log Loss, also known as Logistic Loss or Cross-Entropy Loss, "
        "measures the performance of a classification model "
        "where the prediction input is a probability value "
        "between 0 and 1."
    )

    MAXIMIZE: bool = False

    @staticmethod
    def score(
        true_labels: "DashAIDataset", probs_pred_labels, multiclass=None
    ) -> float:
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
