"""DashAI implementation of XLNet model for English text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class XlnetTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained XLNet model for English text classification.

    XLNet is an autoregressive language model that maximises the expected
    log-likelihood over all permutations of the factorisation order. Unlike BERT,
    XLNet does not rely on a corrupted input and can model bidirectional context
    without masking, often outperforming BERT on various NLP tasks.

    References
    ----------
    - [1] Yang, Z. et al. (2019). "XLNet: Generalised Autoregressive Pretraining
           for Language Understanding." NeurIPS 2019.
    - [2] https://huggingface.co/xlnet-base-cased
    """

    DISPLAY_NAME: str = MultilingualString(
        en="XLNet Transformer",
        es="Transformer XLNet",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Autoregressive XLNet model for English text classification. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Modelo XLNet autorregresivo para clasificación de texto en inglés. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
    )
    COLOR: str = "#37474F"
    ICON: str = "AutoAwesome"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "xlnet-base-cased"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_xlnet"
