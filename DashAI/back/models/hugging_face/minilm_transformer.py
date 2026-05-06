"""DashAI implementation of MiniLM model for efficient English text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class MiniLMTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained MiniLM model for lightweight English text classification.

    MiniLM is a compressed BERT-like model distilled from a larger teacher
    network using deep self-attention distillation. It achieves competitive
    performance while being significantly smaller and faster than BERT, making
    it a good choice for resource-constrained deployments.

    References
    ----------
    - [1] Wang, W. et al. (2020). "MiniLM: Deep Self-Attention Distillation for
           Task-Agnostic Compression of Pre-Trained Transformers." NeurIPS 2020.
    - [2] https://huggingface.co/microsoft/MiniLM-L12-H384-uncased
    """

    DISPLAY_NAME: str = MultilingualString(
        en="MiniLM Transformer",
        es="Transformer MiniLM",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Compact, fast MiniLM model for efficient text classification. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Modelo MiniLM compacto y rápido para clasificación de texto eficiente. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
    )
    COLOR: str = "#0277BD"
    ICON: str = "Speed"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "microsoft/MiniLM-L12-H384-uncased"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_minilm"
