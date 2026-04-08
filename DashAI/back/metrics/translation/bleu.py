"""BLEU (bilingual evaluation understudy) metric implementation for DashAI."""

from typing import TYPE_CHECKING

from DashAI.back.metrics.base_metric import prepare_to_metric
from DashAI.back.metrics.translation_metric import TranslationMetric

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Bleu(TranslationMetric):
    """A class for calculating BLEU scores between source and target sentences.

    BLEU (bilingual evaluation understudy) is an algorithm for evaluating the quality
    of text which has been machine-translated from one natural language to another.

    References
    ----------
    - [1] https://en.wikipedia.org/wiki/BLEU
    """

    MAXIMIZE: bool = True
    DESCRIPTION: str = (
        "BLEU (bilingual evaluation understudy) "
        "measures similarity between generated and reference text "
        "based on n-gram overlap."
    )

    @staticmethod
    def score(
        source_sentences: "DashAIDataset",
        target_sentences: "np.ndarray",
    ) -> float:
        """Calculate the BLEU score between source and target sentences.

        Parameters
        ----------
        source_sentences : DashAIDataset
            Sentences in the original language.
        target_sentences : ndarray
            Sentences in the target language.

        Returns
        -------
        float
            The calculated BLEU score ranging between 0 and 1.
        """
        import evaluate

        metric = evaluate.load("bleu")
        source_sentences, target_sentences = prepare_to_metric(
            source_sentences, target_sentences, "Bleu"
        )
        return metric.compute(
            references=source_sentences, predictions=target_sentences
        )["bleu"]
