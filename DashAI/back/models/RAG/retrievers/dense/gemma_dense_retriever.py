from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._gemma_embedding import (
    TASK_PROMPTS,
    _GemmaEmbedding,
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

TASK_TYPES = list(TASK_PROMPTS.keys())

GEMMA_MODELS: Dict[str, dict] = {
    "google/embeddinggemma-300m": {
        "languages": ["en"],
        "max_seq_length": 8192,
    },
}

GEMMA_MODEL_NAMES = list(GEMMA_MODELS.keys())


class GemmaDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(GEMMA_MODEL_NAMES),
        placeholder="google/embeddinggemma-300m",
        description=MultilingualString(
            en="Gemma embedding model (uses SentenceTransformers API).",
            es="Modelo de embedding Gemma (usa API SentenceTransformers).",
        ),
    )  # type: ignore

    task_type: schema_field(
        enum_field(TASK_TYPES),
        placeholder="search_result",
        description=MultilingualString(
            en="Task type that optimizes the query embedding for a specific use case.",
            es="Tipo de tarea que optimiza el embedding de consulta para un caso de uso específico.",
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


class GemmaDenseRetriever(HuggingFaceDenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = GemmaDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Gemma Embedding Retriever",
        es="Recuperador por Embeddings Gemma",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using Gemma embeddings via SentenceTransformers API.",
        es="Recuperador denso que usa embeddings Gemma mediante API SentenceTransformers.",
    )

    @classmethod
    def get_metadata(cls):
        return build_retriever_metadata(GEMMA_MODELS, "Gemma", len(GEMMA_MODEL_NAMES))

    def _create_embedding(self) -> _GemmaEmbedding:
        model_name = self.params.pop("model_name")
        device = self.params.pop("device")
        overflow_strategy = self.params.pop("overflow_strategy")
        task_type = self.params.pop("task_type")
        model_info = GEMMA_MODELS[model_name]
        return _GemmaEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            task_type=task_type,
        )
