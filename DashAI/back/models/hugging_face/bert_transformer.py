"""DashAI implementation of BERT model for English text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class BertTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained BERT model for English text classification.

    BERT (Bidirectional Encoder Representations from Transformers) pre-trains deep
    bidirectional representations by jointly conditioning on both left and right
    context in all layers. Fine-tuned BERT achieves strong results on a wide range
    of text classification tasks.

    References
    ----------
    - [1] Devlin, J. et al. (2019). "BERT: Pre-training of Deep Bidirectional
           Transformers for Language Understanding." NAACL 2019.
    - [2] https://huggingface.co/bert-base-uncased
    """

    DISPLAY_NAME: str = MultilingualString(
        en="BERT Transformer",
        es="Transformer BERT",
        pt="Transformer BERT",
        de="BERT Transformer",
        zh="BERT Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Bidirectional BERT model for English text classification. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Modelo BERT bidireccional para clasificación de texto en inglés. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Modelo BERT bidirecional para classificação de texto em inglês. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Bidirektionales BERT-Modell für englische Textklassifikation. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
        zh=(
            "双向 BERT 模型，用于英文文本分类。"
            "首次使用时从 Hugging Face 下载权重（需要网络）。"
        ),
    )
    COLOR: str = "#1565C0"
    ICON: str = "Psychology"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "bert-base-uncased"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_bert"
