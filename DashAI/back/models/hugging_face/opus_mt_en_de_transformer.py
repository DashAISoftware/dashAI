"""OpusMtEnDeTransformer model for English-to-German translation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)


class OpusMtEnDeTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for the English-to-German Opus-MT model."""


class OpusMtEnDeTransformer(OpusMtTransformerMixin):
    """Pre-trained transformer for English-to-German translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-en-de`` checkpoint, a MarianMT
    seq2seq model trained on parallel English-German corpora from the OPUS
    collection.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-en-de
    - [2] https://opus.nlpl.eu/
    """

    MODEL_NAME: str = "Helsinki-NLP/opus-mt-en-de"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_opus-mt-en-de"
    SCHEMA = OpusMtEnDeTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT En-De Transformer",
        es="Transformer Opus MT En-De",
        pt="Transformer Opus MT En-De",
        de="Opus MT En-De Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pre-trained transformer for English-German translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer pre-entrenado para traducción inglés-alemán. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Transformer pré-treinado para tradução inglês-alemão. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Vortrainierter Transformer für Englisch-Deutsch-Übersetzung. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
    )
    COLOR: str = "#455A64"
    ICON: str = "Translate"
