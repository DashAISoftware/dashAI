from typing import Dict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._gemma_embedding import _GemmaEmbedding
from DashAI.back.models.RAG.retrievers.dense._hf_metadata_utils import (
    build_retriever_metadata,
)
from DashAI.back.models.RAG.retrievers.dense.huggingface_dense_retriever import (
    METRICS,
    HuggingFaceDenseRetriever,
)

GEMMA_MODELS: Dict[str, dict] = {
    "google/embeddinggemma-300m": {
        "languages": ["en"],
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
        max_length = self.params.pop("max_length")
        self.params.pop("batch_size")
        return _GemmaEmbedding(
            model_name=model_name,
            device=device,
            max_length=max_length,
        )
