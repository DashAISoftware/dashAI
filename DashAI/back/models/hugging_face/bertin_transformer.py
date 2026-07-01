"""DashAI implementation of BERTIN model for Spanish text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class BertinTransformer(HuggingFaceTextClassificationTransformer):
    """Pretrained BERTIN model (Spanish RoBERTa) for Spanish text classification.

    BERTIN is a Spanish RoBERTa model trained on the Spanish portion of mC4 and
    additional Spanish corpora. It applies RoBERTa's improved training recipe to
    Spanish and typically outperforms BETO on Spanish NLP benchmarks. Requires
    the ``sentencepiece`` package for its tokeniser.

    References
    ----------
    - [1] de la Rosa, J. et al. (2022). "BERTIN: Efficient Pre-Training of a
           Spanish Language Model using Perplexity Sampling."
    - [2] https://huggingface.co/bertin-project/bertin-roberta-base-spanish
    """

    DISPLAY_NAME: str = MultilingualString(
        en="BERTIN Spanish RoBERTa",
        es="BERTIN RoBERTa en Español",
        pt="BERTIN RoBERTa em Espanhol",
        de="BERTIN Spanisches RoBERTa",
        zh="BERTIN 西班牙语 RoBERTa",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Spanish RoBERTa (BERTIN) pretrained on large Spanish corpora. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "RoBERTa en español (BERTIN) preentrenada en grandes corpus en español. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "RoBERTa em espanhol (BERTIN) pré-treinada em grandes corpus em espanhol. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
        de=(
            "Spanisches RoBERTa (BERTIN) vortrainiert auf großen spanischen Korpora. "
            "Lädt Gewichte von Hugging Face bei der ersten Verwendung herunter "
            "(Internet erforderlich)."
        ),
        zh=(
            "在大型西班牙语语料库上预训练的 RoBERTa（BERTIN）模型。"
            "首次使用时从 Hugging Face 下载权重（需要网络）。"
        ),
    )
    COLOR: str = "#AD1457"
    ICON: str = "RecordVoiceOver"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "bertin-project/bertin-roberta-base-spanish"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_bertin"
