"""DashAI CHRF metric implementation for translation tasks."""

from typing import TYPE_CHECKING

from DashAI.back.core.utils import MultilingualString
from DashAI.back.metrics.translation_metric import TranslationMetric, prepare_to_metric

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class Chrf(TranslationMetric):
    """A class for calculating CHRF scores between source and target sentences.

    CHRF (Character n-gram F-score) is a metric used for evaluating the quality
    of machine-translated text by comparing it to reference translations
    at the character level.

    References
    ----------
    - [1] https://en.wikipedia.org/wiki/CHRF
    - [2] https://lightning.ai/docs/torchmetrics/stable/text/chrf_score.html
    """

    MAXIMIZE: bool = True
    DESCRIPTION = MultilingualString(
        en=(
            "CHRF (Character n-gram F-score) evaluates machine translation "
            "quality by comparing candidate and reference texts at the "
            "character level. It computes precision, recall, and F-score "
            "over character n-grams, and is especially useful for "
            "morphologically rich languages or short texts."
        ),
        es=(
            "CHRF (Character n-gram F-score) evalúa la calidad de la traducción "
            "automática comparando textos candidatos y de referencia a nivel "
            "de caracteres. Calcula precisión, exhaustividad y F-score "
            "sobre n-gramas de caracteres, y es especialmente útil para "
            "idiomas morfológicamente ricos o textos cortos."
        ),
    )

    @staticmethod
    def score(
        source_sentences: "DashAIDataset", target_sentences: "np.ndarray"
    ) -> float:
        """Calculate the CHRF score between source and target sentences.

        Parameters
        ----------
        source_sentences : DashAIDataset
            Sentences in the original language.
        target_sentences : ndarray
            Sentences in the target language.

        Returns
        -------
        float
            The calculated CHRF score ranging between 0 and 1.
        """
        from torchmetrics.text.chrf import CHRFScore

        chrf_metric = CHRFScore()
        source_sentences, target_sentences = prepare_to_metric(
            source_sentences, target_sentences
        )
        return (
            chrf_metric(
                target_sentences,
                source_sentences,
            )
            .numpy()
            .item()
        )
