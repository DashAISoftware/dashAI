"""DashAI implementation of ModernBERT for text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class ModernBertTransformerSchema(DistilBertTransformerSchema):
    """ModernBERT transformer for efficient long-context text classification."""


class ModernBertTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained ModernBERT model for text classification tasks."""

    DISPLAY_NAME: str = MultilingualString(
        en="ModernBERT Transformer",
        es="Transformer ModernBERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Modern BERT model for efficient and robust text classification.",
        es="Modelo Modern BERT para clasificación de texto eficiente y robusta.",
    )
    COLOR: str = "#455A64"
    ICON: str = "Psychology"
    SCHEMA = ModernBertTransformerSchema
    MODEL_NAME: str = "answerdotai/ModernBERT-base"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_modernbert"
