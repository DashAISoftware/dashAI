"""DashAI implementation of ELECTRA model for English text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class ElectraTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained ELECTRA model for efficient English text classification.

    ELECTRA uses a replaced-token-detection pre-training objective: a generator
    produces plausible token replacements while a discriminator is trained to
    identify which tokens were replaced. This allows ELECTRA to train on all
    input tokens rather than only masked ones, making pre-training more efficient.

    References
    ----------
    - [1] Clark, K. et al. (2020). "ELECTRA: Pre-training Text Encoders as
           Discriminators Rather Than Generators." ICLR 2020.
    - [2] https://huggingface.co/google/electra-small-discriminator
    """

    DISPLAY_NAME: str = MultilingualString(
        en="ELECTRA Transformer",
        es="Transformer ELECTRA",
        pt="Transformer ELECTRA",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Sample-efficient ELECTRA discriminator for text classification. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Discriminador ELECTRA eficiente en muestras para clasificación de texto. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Discriminador ELECTRA eficiente em amostras para classificação de texto. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
    )
    COLOR: str = "#558B2F"
    ICON: str = "ElectricBolt"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "google/electra-small-discriminator"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_electra"
