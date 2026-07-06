from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._gemma_embedding import (
    TASK_PROMPTS,
    _GemmaEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    AGGREGATE,
    TRUNCATE,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

TASK_TYPES = list(TASK_PROMPTS.keys())

GEMMA_MODELS: Dict[str, dict] = {
    "google/embeddinggemma-300m": {
        "languages": ["en"],
        "max_seq_length": 8192,
    },
}

GEMMA_MODEL_NAMES = list(GEMMA_MODELS.keys())


class GemmaEmbeddingSchema(BaseSchema):
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


class GemmaEmbedding(DenseEmbedding):
    SCHEMA = GemmaEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:gemma", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="Gemma Embedding",
        es="Embedding Gemma",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using Gemma models via SentenceTransformers API.",
        es="Embeddings densos usando modelos Gemma mediante API SentenceTransformers.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        overflow_strategy = self.params.get("overflow_strategy", "truncate")
        task_type = self.params["task_type"]
        model_info = GEMMA_MODELS[model_name]
        self._embedding = _GemmaEmbedding(
            model_name=model_name,
            device=device,
            model_max_length=model_info["max_seq_length"],
            overflow_strategy=overflow_strategy,
            task_type=task_type,
        )

    def load(self):
        self._embedding.load()

    def encode(self, text: str):
        return self._embedding.encode(text)

    def batch_encode(self, texts: List[str]):
        return self._embedding.batch_encode(texts)

    def save(self):
        pass

    def train(self, **kwargs):
        return
