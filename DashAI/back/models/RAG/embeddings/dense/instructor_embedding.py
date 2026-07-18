from typing import Dict, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense._instructor_embedding import (
    _InstructorEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

INSTRUCTOR_MODELS: Dict[str, dict] = {
    "hkunlp/instructor-base": {
        "languages": ["en"],
    },
    "hkunlp/instructor-large": {
        "languages": ["en"],
    },
    "hkunlp/instructor-xl": {
        "languages": ["en"],
    },
}

INSTRUCTOR_MODEL_NAMES = list(INSTRUCTOR_MODELS.keys())


class InstructorEmbeddingSchema(BaseSchema):
    """Configuration schema for :class:`InstructorEmbedding`.

    Attributes:
        model_name: INSTRUCTOR model for instruction-tuned embedding generation.
        instruction: Instruction text that guides the embedding model.
        device: Device to run the model on.
    """

    model_name: schema_field(
        enum_field(INSTRUCTOR_MODEL_NAMES),
        placeholder="hkunlp/instructor-base",
        description=MultilingualString(
            en="INSTRUCTOR model for instruction-tuned embedding generation.",
            es="Modelo INSTRUCTOR para generación de embeddings ajustados"
            " por instrucción.",
        ),
    )  # type: ignore

    instruction: schema_field(
        string_field(),
        placeholder="Represent the document for retrieval:",
        description=MultilingualString(
            en="Instruction text that guides the embedding model.",
            es="Texto de instrucción que guía al modelo de embedding.",
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


class InstructorEmbedding(DenseEmbedding):
    """Dense embeddings using INSTRUCTOR instruction-tuned models.

    Wraps :class:`_InstructorEmbedding` and exposes it as a DashAI component
    with a configurable schema (:class:`InstructorEmbeddingSchema`).

    Prepends a user-defined instruction string to every input text.

    FLAGS:
        FAMILY:instructor: Groups this model under the INSTRUCTOR family.
        huggingface: Marks the model family as HuggingFace-based.
    """

    SCHEMA = InstructorEmbeddingSchema
    FLAGS: list[str] = ["FAMILY:instructor", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="INSTRUCTOR Embedding",
        es="Embedding INSTRUCTOR",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense embeddings using INSTRUCTOR instruction-tuned models.",
        es="Embeddings densos usando modelos INSTRUCTOR ajustados por instrucción.",
    )

    def __init__(self, **kwargs):
        """Initialise the embedding by validating parameters and creating the internal
        model.

        Args:
            **kwargs: Configuration matching :class:`InstructorEmbeddingSchema`.
        """
        self.params = self.validate_and_transform(kwargs)
        model_name = self.params["model_name"]
        device = self.params["device"]
        instruction = self.params["instruction"]
        self._embedding = _InstructorEmbedding(
            model_name=model_name,
            device=device,
            instruction=instruction,
        )

    def load(self):
        """Load the INSTRUCTOR model."""
        self._embedding.load()

    def encode(self, text: str):
        """Encode a single text into a dense embedding with the configured instruction.

        Args:
            text: Input string.

        Returns:
            A 1-D NumPy array of shape ``(embedding_dim,)``.
        """
        return self._embedding.encode(text)

    def batch_encode(self, texts: List[str]):
        """Encode a batch of texts into dense embeddings with the configured
        instruction.

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
