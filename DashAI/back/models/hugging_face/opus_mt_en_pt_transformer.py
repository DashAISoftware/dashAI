"""OpusMtEnPtTransformer model for English to Portuguese translation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformerSchema,
)


class OpusMtEnPtTransformerSchema(OpusMtEnESTransformerSchema):
    """Schema for the English to Portuguese Opus-MT model."""


class OpusMtEnPtTransformer(OpusMtTransformerMixin):
    """Pretrained transformer for English to Portuguese translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-en-pt`` checkpoint, a MarianMT
    seq2seq model trained on parallel English to Portuguese corpora from the OPUS
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
        pt="Transformer Opus MT En-Pt",
        de="Opus MT En-Pt Transformer",
        zh="Opus MT 英葡翻译 Transformer",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pretrained transformer for English to Portuguese translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer preentrenado para traducción inglés-portugués. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Transformer pré-treinado para tradução inglês-português. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Vortrainierter Transformer für Englisch-Portugiesisch-Übersetzung. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
        zh=(
            "用于英语到葡萄牙语翻译的预训练 Transformer。"
            "首次使用时从 Hugging Face 下载权重（需要网络）。"
        ),
    )
    COLOR: str = "#2E7D32"
    ICON: str = "Translate"
