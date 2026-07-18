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
    """Configuration schema for :class:`GemmaEmbedding`.

    Attributes:
        model_name: Gemma embedding model (uses SentenceTransformers API).
        task_type: Task type that optimises the query embedding for a specific use case.
        overflow_strategy: Strategy for chunks exceeding model max sequence length.
        device: Device to run the model on.
    """

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
            es="Tipo de tarea que optimiza el embedding de consulta para"
            " un caso de uso específico.",
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
    """Dense embeddings using Gemma models via the SentenceTransformers API.

    Wraps :class:`_GemmaEmbedding` and exposes it as a DashAI component with
    a configurable schema (:class:`GemmaEmbeddingSchema`).

    Supports task-aware query prompts (search, QA, classification, etc.).

    FLAGS:
        FAMILY:gemma: Groups this model under the Gemma family.
        huggingface: Marks the model family as HuggingFace-based.
    """

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
        """Initialise the embedding by validating parameters and creating the internal model.

        Args:
            **kwargs: Configuration matching :class:`GemmaEmbeddingSchema`.
        """  # noqa: E501
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
        """Load the Gemma model via SentenceTransformers."""
        self._embedding.load()

    def encode(self, text: str):
        """Encode a single text into a dense embedding with the configured task prompt.

        Args:
            text: Input string.

        Returns:
            A 1-D NumPy array of shape ``(embedding_dim,)``.
        """
        return self._embedding.encode(text)

    def batch_encode(self, texts: List[str]):
        """Encode a batch of texts into dense embeddings with document prompts.

        Args:
            texts: List of input strings.

        Returns:
            A ``(batch, embedding_dim)`` float32 NumPy array.
        """
        return self._embedding.batch_encode(texts)

    def save(self):
        """No-op. Persistence is handled externally."""

    def train(self, **kwargs):
        """No-op. Pre-trained models are used as-is."""
