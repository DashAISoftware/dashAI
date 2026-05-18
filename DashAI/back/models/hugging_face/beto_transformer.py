"""DashAI implementation of BETO model for Spanish text classification."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.hugging_face.distilbert_transformer import (
    DistilBertTransformerSchema,
)


class BetoTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained BETO model for Spanish text classification.

    BETO is a Spanish BERT trained on the Spanish Wikipedia and other Spanish
    corpora using the whole-word masking strategy. It achieves state-of-the-art
    results on several Spanish NLP benchmarks. Particularly useful for tasks
    involving Spanish text.

    References
    ----------
    - [1] Cañete, J. et al. (2020). "Spanish Pre-Trained BERT Model and
           Evaluation Data." PML4DC at ICLR 2020.
    - [2] https://huggingface.co/dccuchile/bert-base-spanish-wwm-cased
    """

    DISPLAY_NAME: str = MultilingualString(
        en="BETO Spanish BERT",
        es="BETO BERT en Español",
        pt="BETO BERT em Espanhol",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Spanish BERT (BETO) pre-trained on Spanish corpora. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "BERT en español (BETO) pre-entrenado en corpus en español. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "BERT em espanhol (BETO) pré-treinado em corpus em espanhol. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
    )
    COLOR: str = "#C62828"
    ICON: str = "RecordVoiceOver"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "dccuchile/bert-base-spanish-wwm-cased"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_beto"
