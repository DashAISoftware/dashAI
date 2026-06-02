from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._bert_embedding import (
    CLS,
    CONCAT_2,
    CONCAT_3,
    CONCAT_4,
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

TRUNCATE = "truncate"
AGGREGATE = "aggregate"
DISTILBERT_POOLING_STRATEGIES = [CLS, MEAN, MAX, CONCAT_2, CONCAT_3, CONCAT_4]

DISTILBERT_MODELS: Dict[str, dict] = {
    "distilbert/distilbert-base-cased": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-base-uncased": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-base-multilingual-cased": {
        "languages": [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ca", "fi",
            "ar", "zh", "ja", "ko", "ru", "tr", "hi", "sv", "da", "no",
            "cs", "ro", "el", "he", "hu", "th", "vi", "id", "ms", "bg",
            "hr", "sk", "sl", "sr", "uk", "et", "lv", "lt", "fa", "ur",
            "mk", "af", "bn", "multi",
        ],
        "max_seq_length": 512,
    },
    "distilbert/distilbert-roberta-base": {
        "languages": ["en"],
        "max_seq_length": 512,
    },
}

DISTILBERT_MODEL_NAMES = list(DISTILBERT_MODELS.keys())


class DistilBERTDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(DISTILBERT_MODEL_NAMES),
        placeholder="distilbert/distilbert-base-cased",
        description=MultilingualString(
            en="DistilBERT model for embedding generation.",
            es="Modelo DistilBERT para generación de embeddings.",
        ),
    )  # type: ignore

    overflow_strategy: schema_field(
        enum_field([TRUNCATE, AGGREGATE]),
        placeholder=TRUNCATE,
        description=MultilingualString(
            en="Strategy for chunks exceeding model max sequence length.",
            es="Estrategia para fragmentos que exceden la longitud máxima del modelo.",
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
        enum_field(DISTILBERT_POOLING_STRATEGIES),
        placeholder=MEAN,
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings.",
            es="Estrategia de pooling para agregar embeddings de tokens.",
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


class DistilBERTDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = DistilBERTDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="DistilBERT Embedding Retriever",
        es="Recuperador por Embeddings DistilBERT",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using DistilBERT embeddings with configurable pooling.",
        es="Recuperador denso que usa embeddings DistilBERT con pooling configurable.",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(DISTILBERT_MODELS, "DistilBERT", len(DISTILBERT_MODEL_NAMES))

    def _create_embedding(self) -> _BERTEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        overflow_strategy = self.params.pop("overflow_strategy")
        pooling_strategy = self.params.pop("pooling_strategy")
        model_info = DISTILBERT_MODELS[model_name]
        return _BERTEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            pooling_strategy=pooling_strategy,
        )
