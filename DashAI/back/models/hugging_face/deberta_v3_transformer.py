"""DashAI implementation of DeBERTa-v3 for text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class DebertaV3TransformerSchema(DistilBertTransformerSchema):
    """DeBERTa-v3 transformer for high-quality text classification."""


class DebertaV3Transformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained DeBERTa-v3 model for text classification tasks."""

    DISPLAY_NAME: str = MultilingualString(
        en="DeBERTa-v3 Transformer",
        es="Transformer DeBERTa-v3",
    )
    DESCRIPTION: str = MultilingualString(
        en="DeBERTa-v3 model for robust text classification performance.",
        es="Modelo DeBERTa-v3 para clasificación de texto robusta.",
    )
    COLOR: str = "#1E88E5"
    ICON: str = "Psychology"
    SCHEMA = DebertaV3TransformerSchema
    MODEL_NAME: str = "microsoft/deberta-v3-base"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_deberta_v3"
