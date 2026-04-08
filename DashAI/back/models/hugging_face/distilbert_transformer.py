"""DashAI implementation of DistilBERT model for english classification."""

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.base_text_classification_transformer import (
    HuggingFaceTextClassificationTransformer,
)
from DashAI.back.models.utils import GPU_OR_CPU, GPU_OR_CPU_PLACEHOLDER


class DistilBertTransformerSchema(BaseSchema):
    """Distilbert is a transformer that allows you to classify text in English.
    The implementation is based on huggingface distilbert-base in the case of
    the uncased model, i.e. distilbert-base-uncased.
    """

    num_train_epochs: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Total number of training epochs to perform.",
            es="Número total de épocas de entrenamiento a realizar.",
        ),
        alias=MultilingualString(en="Num train epochs", es="Número de épocas"),
    )  # type: ignore
    batch_size: schema_field(
        int_field(ge=1),
        placeholder=16,
        description=MultilingualString(
            en="The batch size per GPU/TPU core/CPU for training",
            es="El tamaño de lote por núcleo GPU/TPU/CPU para entrenamiento",
        ),
        alias=MultilingualString(en="Batch size", es="Tamaño de lote"),
    )  # type: ignore
    learning_rate: schema_field(
        float_field(ge=0.0),
        placeholder=3e-5,
        description=MultilingualString(
            en="The initial learning rate for AdamW optimizer",
            es="La tasa de aprendizaje inicial para el optimizador AdamW",
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore
    device: schema_field(
        enum_field(enum=GPU_OR_CPU),
        placeholder=GPU_OR_CPU_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware on which the training is run. If available, GPU is "
                "recommended for efficiency reasons. Otherwise, use CPU."
            ),
            es=(
                "Hardware en el que se ejecuta el entrenamiento. Si está disponible, "
                "se recomienda GPU por razones de eficiencia. De lo contrario, use CPU."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore
    weight_decay: schema_field(
        float_field(ge=0.0),
        placeholder=0.01,
        description=MultilingualString(
            en=(
                "Weight decay is a regularization technique used in training "
                "neural networks to prevent overfitting. In the context of the AdamW "
                "optimizer, the 'weight_decay' parameter is the rate at which the "
                "weights of all layers are reduced during training, provided that "
                "this rate is not zero."
            ),
            es=(
                "Weight decay es una técnica de regularización usada en el "
                "entrenamiento de redes neuronales para prevenir sobreajuste. En el "
                "contexto del optimizador AdamW, el parámetro 'weight_decay' es la "
                "tasa a la cual los pesos de todas las capas se reducen durante el "
                "entrenamiento, siempre que esta tasa no sea cero."
            ),
        ),
        alias=MultilingualString(en="Weight decay", es="Decaimiento de pesos"),
    )  # type: ignore

    log_train_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Log metrics for train split every n epochs during training. "
                "If None, it won't log per epoch."
            ),
            es=(
                "Registrar métricas del split de entrenamiento cada n épocas. "
                "Si es None, no registrará por época."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N epochs", es="Registrar entrenamiento cada N épocas"
        ),
    )  # type: ignore

    log_train_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Log metrics for train split every n steps during training. "
                "If None, it won't log per step."
            ),
            es=(
                "Registrar métricas del split de entrenamiento cada n pasos. "
                "Si es None, no registrará por paso."
            ),
        ),
        alias=MultilingualString(
            en="Log train every N steps", es="Registrar entrenamiento cada N pasos"
        ),
    )  # type: ignore

    log_validation_every_n_epochs: schema_field(
        none_type(int_field(ge=1)),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Log metrics for validation split every n epochs during training. "
                "If None, it won't log per epoch."
            ),
            es=(
                "Registrar métricas del split de validación cada n épocas. "
                "Si es None, no registrará por época."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N epochs", es="Registrar validación cada N épocas"
        ),
    )  # type: ignore

    log_validation_every_n_steps: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Log metrics for validation split every n steps during training. "
                "If None, it won't log per step."
            ),
            es=(
                "Registrar métricas del split de validación cada n pasos. "
                "Si es None, no registrará por paso."
            ),
        ),
        alias=MultilingualString(
            en="Log validation every N steps", es="Registrar validación cada N pasos"
        ),
    )  # type: ignore


class DistilBertTransformer(HuggingFaceTextClassificationTransformer):
    """Pre-trained transformer DistilBERT allowing English text classification.

    DistilBERT is a small, fast, cheap and light Transformer model trained by
    distilling BERT base.
    It has 40% less parameters than bert-base-uncased, runs 60% faster while preserving
    over 95% of BERT's performances as measured on the GLUE language understanding
    benchmark [1].

    References
    ----------
    - [1] https://huggingface.co/docs/transformers/model_doc/distilbert
    """

    DISPLAY_NAME: str = MultilingualString(
        en="DistilBERT Transformer",
        es="Transformer DistilBERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Distilled BERT model for efficient text classification.",
        es="Modelo BERT destilado para clasificación de texto eficiente.",
    )
    COLOR: str = "#96008E"
    ICON: str = "Psychology"
    SCHEMA = DistilBertTransformerSchema
    MODEL_NAME: str = "distilbert-base-uncased"
    TEMP_CHECKPOINT_DIR: str = "DashAI/back/user_models/temp_checkpoints_distilbert"
