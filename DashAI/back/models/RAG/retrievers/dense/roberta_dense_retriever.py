from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._bert_embedding import (
    MAX,
    MEAN,
    _BERTEmbedding,
)
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

ROBERTA_POOLING_STRATEGIES = [MEAN, MAX]

ROBERTA_MODELS: Dict[str, dict] = {
    "FacebookAI/roberta-base": {
        "languages": ["en"],
    },
    "FacebookAI/roberta-large": {
        "languages": ["en"],
    },
    "FacebookAI/xlm-roberta-base": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
    "FacebookAI/xlm-roberta-large": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
    },
}

ROBERTA_MODEL_NAMES = list(ROBERTA_MODELS.keys())


class RoBERTaDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(ROBERTA_MODEL_NAMES),
        placeholder="FacebookAI/roberta-base",
        description=MultilingualString(
            en="RoBERTa / XLM-RoBERTa model for embedding generation.",
            es="Modelo RoBERTa / XLM-RoBERTa para generación de embeddings.",
        ),
    )  # type: ignore

    max_length: schema_field(
        int_field(ge=1),
        placeholder=512,
        description=MultilingualString(
            en="Maximum sequence length for tokenization.",
            es="Longitud máxima de secuencia para tokenización.",
        ),
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        placeholder=32,
        description=MultilingualString(
            en="Number of samples to process at once.",
            es="Número de muestras a procesar a la vez.",
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(["cpu", "cuda"]),
        placeholder="cpu",
        description=MultilingualString(
            en="Device to run the model on.",
            es="Dispositivo para ejecutar el modelo.",
        ),
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(ROBERTA_POOLING_STRATEGIES),
        placeholder=MEAN,
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings. RoBERTa CLS token is not trained for similarity.",
            es="Estrategia de pooling para agregar embeddings de tokens. El token CLS de RoBERTa no está entrenado para similitud.",
        ),
    )  # type: ignore

    similarity_metric: schema_field(
        enum_field(enum=METRICS),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing dense vectors.",
            es="Métrica de distancia para comparar vectores densos.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description=MultilingualString(
            en="Number of chunks to select.",
            es="Número de fragmentos a seleccionar.",
        ),
    )  # type: ignore


class RoBERTaDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = RoBERTaDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="RoBERTa Embedding Retriever",
        es="Recuperador por Embeddings RoBERTa",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using RoBERTa / XLM-RoBERTa embeddings with mean/max pooling.",
        es="Recuperador denso que usa embeddings RoBERTa / XLM-RoBERTa con pooling mean/max.",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(ROBERTA_MODELS, "RoBERTa", len(ROBERTA_MODEL_NAMES))

    def _create_embedding(self) -> _BERTEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        max_length = self.params.pop("max_length")
        pooling_strategy = self.params.pop("pooling_strategy")
        self.params.pop("batch_size")
        return _BERTEmbedding(
            model_name=model_name,
            device=device,
            max_length=max_length,
            pooling_strategy=pooling_strategy,
        )
