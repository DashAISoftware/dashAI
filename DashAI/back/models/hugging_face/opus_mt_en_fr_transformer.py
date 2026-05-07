"""OpusMtEnFrTransformer model for English-to-French translation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)


class OpusMtEnFrTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for the English-to-French Opus-MT model."""


class OpusMtEnFrTransformer(OpusMtTransformerMixin):
    """Pre-trained transformer for English-to-French translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-en-fr`` checkpoint, a MarianMT
    seq2seq model trained on parallel English-French corpora from the OPUS
    collection.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-en-fr
    - [2] https://opus.nlpl.eu/
    """

    MODEL_NAME: str = "Helsinki-NLP/opus-mt-en-fr"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_opus-mt-en-fr"
    SCHEMA = OpusMtEnFrTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT En-Fr Transformer",
        es="Transformer Opus MT En-Fr",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pre-trained transformer for English-French translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer pre-entrenado para traducción inglés-francés. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
    )
    COLOR: str = "#1976D2"
    ICON: str = "Translate"
