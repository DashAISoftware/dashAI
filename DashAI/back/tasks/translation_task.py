"""DashAI Translation Task."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.supervised_task import SupervisedTask
from DashAI.back.types.value_types import Text


class TranslationTask(SupervisedTask):
    """Task for sequence-to-sequence machine translation between languages.

    Translation tasks take a single ``Text`` input column (source language) and
    produce a single ``Text`` output column (target language). The compatible
    metrics are BLEU, CHRF, and TER, which measure n-gram overlap, character-level
    F-score, and translation edit rate against reference translations respectively.
    """

    COMPATIBLE_COMPONENTS = ["Bleu", "Chrf", "Ter"]

    SCORING_PROFILES = {
        "translation_quality": {
            "description": "Translation Quality",
            "weights": {"Bleu": 0.5, "Chrf": 0.5},
        },
        "translation_balanced": {
            "description": "Translation Balanced",
            "weights": {"Bleu": 0.4, "Chrf": 0.3, "Ter": 0.3},
        },
    }

    metadata: dict = {
        "inputs_types": [Text],
        "outputs_types": [Text],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }
    DESCRIPTION: str = MultilingualString(
        en="Convert text from one language to another preserving meaning.",
        es="Convierte texto de un idioma a otro preservando el significado.",
        pt="Converte texto de um idioma para outro preservando o significado.",
        de=(
            "Text von einer Sprache in eine andere übersetzen, wobei die Bedeutung "
            "erhalten bleibt."
        ),
    )

    DISPLAY_NAME: str = MultilingualString(
        en="Translation", es="Traducción", pt="Tradução", de="Übersetzung"
    )
