"""TER (Translation Edit Rate) metric implementation for DashAI."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.base_metric import prepare_to_metric
from DashAI.back.metrics.translation_metric import TranslationMetric

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Ter(TranslationMetric):
    """A class for calculating TER scores between source and target sentences.

    TER (Translation Edit Rate, also called Translation Error Rate) is a metric
    to quantify the edit operations requiered to match a reference translation.

    References
    ----------
    [1] https://huggingface.co/spaces/evaluate-metric/ter
    """

    MAXIMIZE: bool = False
    DESCRIPTION: str = (
        "TER (Translation Edit Rate) measures the number of edits "
        "needed to change a system output into one of the references."
    )

    @staticmethod
    def score(source_sentences: "DashAIDataset", target_sentences):
        """Calculate the TER score between source and target sentences.

        Parameters
        ----------
        source_sentences : DashAIDataset
            Sentences in the original language.
        target_sentences : ndarray
            Sentences in the target language.

        Returns
        -------
        float
            The calculated score.
        """
        import evaluate

        metric = evaluate.load("ter")
        source_sentences, target_sentences = prepare_to_metric(
            source_sentences, target_sentences, "Ter"
        )
        return metric.compute(
            references=source_sentences, predictions=target_sentences
        )["score"]
