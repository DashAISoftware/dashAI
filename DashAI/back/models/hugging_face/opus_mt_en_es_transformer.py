"""OpusMtEnESTransformer model for English-to-Spanish translation."""

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_opus_mt_transformer import (
    OpusMtTransformerMixin,
)
from DashAI.back.models.utils import GPU_OR_CPU, GPU_OR_CPU_PLACEHOLDER


class OpusMtEnESTransformerSchema(BaseSchema):
    """Schema for Opus-MT translation models (MarianMT architecture).

    Shared by all Helsinki-NLP Opus-MT language-pair wrappers. Controls
    training duration, batch size, learning rate, device, regularization, and
    metric-logging frequency.
    """

    num_train_epochs: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Total number of training epochs to perform.",
            es="Número total de épocas de entrenamiento a realizar.",
            pt="Número total de épocas de treinamento a realizar.",
        ),
        alias=MultilingualString(
            en="Num train epochs", es="Número de épocas", pt="Número de épocas"
        ),
    )  # type: ignore
    batch_size: schema_field(
        int_field(ge=1),
        placeholder=4,
        description=MultilingualString(
            en="The batch size per GPU/TPU core/CPU for training.",
            es="El tamaño de lote por núcleo GPU/TPU/CPU para entrenamiento.",
            pt="O tamanho do lote por núcleo GPU/TPU/CPU para treinamento.",
        ),
        alias=MultilingualString(
            en="Batch size", es="Tamaño de lote", pt="Tamanho do lote"
        ),
    )  # type: ignore
    learning_rate: schema_field(
        float_field(ge=0.0),
        placeholder=2e-5,
        description=MultilingualString(
            en="The initial learning rate for AdamW optimizer.",
            es="La tasa de aprendizaje inicial para el optimizador AdamW.",
            pt="A taxa de aprendizado inicial para o otimizador AdamW.",
        ),
        alias=MultilingualString(
            en="Learning rate", es="Tasa de aprendizaje", pt="Taxa de aprendizado"
        ),
    )  # type: ignore
    device: schema_field(
        enum_field(enum=GPU_OR_CPU),
        placeholder=GPU_OR_CPU_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware on which training is run. GPU is recommended when "
                "available. If GPU is selected, all available GPUs are used."
            ),
            es=(
                "Hardware en el que se ejecuta el entrenamiento. Se recomienda "
                "GPU cuando está disponible. Si se selecciona GPU, se usan "
                "todas las GPUs disponibles."
            ),
            pt=(
                "Hardware no qual o treinamento é executado. GPU é recomendada "
                "quando disponível. Se GPU for selecionada, todas as GPUs "
                "disponíveis são usadas."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo", pt="Dispositivo"),
    )  # type: ignore
    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.01,
        description=MultilingualString(
            en=(
                "L2 regularization coefficient applied via the AdamW optimizer "
                "to prevent overfitting."
            ),
            es=(
                "Coeficiente de regularización L2 aplicado mediante el "
                "optimizador AdamW para prevenir sobreajuste."
            ),
            pt=(
                "Coeficiente de regularização L2 aplicado pelo otimizador AdamW "
                "para evitar overfitting."
            ),
        ),
        alias=MultilingualString(
            en="Weight decay", es="Decaimiento de pesos", pt="Decaimento de pesos"
        ),
    )  # type: ignore
    log_train_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=("Log train metrics every N epochs. None disables per-epoch logging."),
            es=(
                "Registrar métricas de entrenamiento cada N épocas. "
                "None desactiva el registro por época."
            ),
            pt=(
                "Registrar métricas de treinamento a cada N épocas. "
                "None desativa o registro por época."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N epochs",
            es="Registrar entrenamiento cada N épocas",
            pt="Registrar treinamento a cada N épocas",
        ),
    )  # type: ignore
    log_train_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=("Log train metrics every N steps. None disables per-step logging."),
            es=(
                "Registrar métricas de entrenamiento cada N pasos. "
                "None desactiva el registro por paso."
            ),
            pt=(
                "Registrar métricas de treinamento a cada N passos. "
                "None desativa o registro por passo."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N steps",
            es="Registrar entrenamiento cada N pasos",
            pt="Registrar treinamento a cada N passos",
        ),
    )  # type: ignore
    log_validation_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Log validation metrics every N epochs. "
                "None disables per-epoch logging."
            ),
            es=(
                "Registrar métricas de validación cada N épocas. "
                "None desactiva el registro por época."
            ),
            pt=(
                "Registrar métricas de validação a cada N épocas. "
                "None desativa o registro por época."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N epochs",
            es="Registrar validación cada N épocas",
            pt="Registrar validação a cada N épocas",
        ),
    )  # type: ignore
    log_validation_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Log validation metrics every N steps. None disables per-step logging."
            ),
            es=(
                "Registrar métricas de validación cada N pasos. "
                "None desactiva el registro por paso."
            ),
            pt=(
                "Registrar métricas de validação a cada N passos. "
                "None desativa o registro por passo."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N steps",
            es="Registrar validación cada N pasos",
            pt="Registrar validação a cada N passos",
        ),
    )  # type: ignore


class OpusMtEnESTransformer(OpusMtTransformerMixin):
    """Pre-trained transformer for English-to-Spanish translation.

    Fine-tunes the Helsinki-NLP ``opus-mt-en-es`` checkpoint, a MarianMT
    seq2seq model trained on parallel English-Spanish corpora from the OPUS
    collection. Supports direct translation without pivot languages.

    References
    ----------
    - [1] https://huggingface.co/Helsinki-NLP/opus-mt-en-es
    - [2] https://opus.nlpl.eu/
    """

    MODEL_NAME: str = "Helsinki-NLP/opus-mt-en-es"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_opus-mt-en-es"
    SCHEMA = OpusMtEnESTransformerSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Opus MT En-Es Transformer",
        es="Transformer Opus MT En-Es",
        pt="Transformer Opus MT En-Es",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Pre-trained transformer for English-Spanish translation. "
            "Downloads weights from Hugging Face on first use (internet required)."
        ),
        es=(
            "Transformer pre-entrenado para traducción inglés-español. "
            "Descarga pesos de Hugging Face en el primer uso (requiere internet)."
        ),
        pt=(
            "Transformer pré-treinado para tradução inglês-espanhol. "
            "Baixa os pesos do Hugging Face no primeiro uso (requer internet)."
        ),
    )
    COLOR: str = "#FFA500"
    ICON: str = "Translate"
