"""OpusMtEnPtTransformer model for English-to-Portuguese translation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)


class OpusMtEnPtTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for the English-to-Portuguese Opus-MT model."""


class OpusMtEnPtTransformer(OpusMtTransformerMixin):
    """Pre-trained transformer for English-to-Portuguese translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-en-pt`` checkpoint, a MarianMT
    seq2seq model trained on parallel English-Portuguese corpora from the OPUS
    collection.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-en-pt
    - [2] https://opus.nlpl.eu/
    """

    MODEL_NAME: str = "Helsinki-NLP/opus-mt-en-pt"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_opus-mt-en-pt"
    SCHEMA = OpusMtEnPtTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT En-Pt Transformer",
        es="Transformer Opus MT En-Pt",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pre-trained transformer for English-Portuguese translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer pre-entrenado para traducción inglés-portugués. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
    )
    COLOR: str = "#2E7D32"
    ICON: str = "Translate"
