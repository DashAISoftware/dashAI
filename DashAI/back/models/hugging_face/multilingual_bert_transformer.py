"""DashAI implementation of Multilingual BERT for multilingual text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class MultilingualBertTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained Multilingual BERT for cross-lingual text classification.

    mBERT (Multilingual BERT) is a single BERT model pre-trained on the Wikipedia
    text of 104 languages. It uses a shared vocabulary and can be fine-tuned on a
    task in one language and applied to another (zero-shot cross-lingual transfer).

    References
    ----------
    - [1] Devlin, J. et al. (2019). "BERT: Pre-training of Deep Bidirectional
           Transformers for Language Understanding." NAACL 2019.
    - [2] https://huggingface.co/bert-base-multilingual-cased
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Multilingual BERT Transformer",
        es="Transformer BERT Multilingüe",
        pt="Transformer BERT Multilingual",
        de="Mehrsprachiger BERT Transformer",
        zh="多语言 BERT Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "BERT pre-trained on 104 languages for multilingual text classification. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "BERT pre-entrenado en 104 idiomas para clasificación de texto "
            "multilingüe. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "BERT pré-treinado em 104 idiomas para classificação de texto "
            "multilingual. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "BERT vortrainiert auf 104 Sprachen für mehrsprachige Textklassifikation. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
        zh=(
            "在 104 种语言上预训练的 BERT，用于多语言文本分类。"
            "首次使用时从 Hugging Face 下载权重（需要网络）。"
        ),
    )
    COLOR: str = "#283593"
    ICON: str = "Translate"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "bert-base-multilingual-cased"
    TEMP_CHECKPOINT_DIR: str = (
        "DashAI/back/user_models/temp_checkpoints_multilingual_bert"
    )
