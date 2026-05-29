"""DashAI implementation of XLM-RoBERTa model for multilingual text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class XlmRobertaTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained XLM-RoBERTa model for multilingual text classification.

    XLM-RoBERTa is a multilingual version of RoBERTa trained on 2.5 TB of
    filtered CommonCrawl data covering 100 languages. It achieves strong
    performance on cross-lingual classification without language-specific
    fine-tuning. Requires the ``sentencepiece`` package for its tokeniser.

    References
    ----------
    - [1] Conneau, A. et al. (2020). "Unsupervised Cross-lingual Representation
           Learning at Scale." ACL 2020.
    - [2] https://huggingface.co/xlm-roberta-base
    """

    DISPLAY_NAME: str = MultilingualString(
        en="XLM-RoBERTa Transformer",
        es="Transformer XLM-RoBERTa",
        pt="Transformer XLM-RoBERTa",
        de="XLM-RoBERTa Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Multilingual RoBERTa for cross-lingual text classification "
            "(100 languages). "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "RoBERTa multilingüe para clasificación de texto entre idiomas "
            "(100 idiomas). "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "RoBERTa multilingual para classificação de texto entre idiomas "
            "(100 idiomas). "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Mehrsprachiges RoBERTa für sprachübergreifende Textklassifikation "
            "(100 Sprachen). "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
    )
    COLOR: str = "#6A1B9A"
    ICON: str = "Language"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "xlm-roberta-base"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_xlm_roberta"
