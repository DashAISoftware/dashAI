"""OpusMtFrEnTransformer model for French-to-English translation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)


class OpusMtFrEnTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for the French-to-English Opus-MT model."""


class OpusMtFrEnTransformer(OpusMtTransformerMixin):
    """Pre-trained transformer for French-to-English translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-fr-en`` checkpoint, a MarianMT
    seq2seq model trained on parallel French-English corpora from the OPUS
    collection.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-fr-en
    - [2] https://opus.nlpl.eu/
    """

    MODEL_NAME: str = "Helsinki-NLP/opus-mt-fr-en"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_opus-mt-fr-en"
    SCHEMA = OpusMtFrEnTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT Fr-En Transformer",
        es="Transformer Opus MT Fr-En",
        pt="Transformer Opus MT Fr-En",
        de="Opus MT Fr-En Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pre-trained transformer for French-English translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer pre-entrenado para traducción francés-inglés. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Transformer pré-treinado para tradução francês-inglês. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Vortrainierter Transformer für Französisch-Englisch-Übersetzung. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
    )
    COLOR: str = "#0097A7"
    ICON: str = "Translate"
