from typing import List

import numpy as np
from openai import OpenAI

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.schema_fields.enum_field import enum_field
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.core.schema_fields.string_field import string_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

# OpenAI caps the number of inputs per embeddings request (2048 for the
# text-embedding-ada-002 / text-embedding-3-* models).
OPENAI_MAX_INPUTS_PER_REQUEST = 2048


def _sanitize_input(text: str) -> str:
    """Return a valid embedding input for ``text``.

    OpenAI rejects empty/whitespace-only strings. A single space is a
    valid, semantically neutral stand-in that preserves the row count
    when encoding batches of chunks.

    Parameters
    ----------
    text : str
        The input string to sanitize.

    Returns
    -------
    str
        ``text`` when it is non-blank, otherwise a single space.
    """
    return text if text and text.strip() else " "


class OpenAIEmbeddingSchema(BaseSchema):
    """Configuration schema for :class:`OpenAIEmbedding`.

    Attributes:
        model_name: OpenAI embedding model to use.
        api_key: OpenAI API key.
    """

    model_name: schema_field(
        enum_field(
            [
                "text-embedding-ada-002",
                "text-embedding-3-small",
                "text-embedding-3-large",
            ]
        ),
        placeholder="text-embedding-3-small",
        description=MultilingualString(
            en="OpenAI embedding model to use.",
            es="Modelo de embedding de OpenAI a utilizar.",
        ),
    )  # type: ignore

    api_key: schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en="OpenAI API key.",
            es="Clave API de OpenAI.",
        ),
    )  # type: ignore


class OpenAIEmbedding(DenseEmbedding):
    """Dense embeddings via the OpenAI Embeddings API.

    Supports ``text-embedding-ada-002``, ``text-embedding-3-small``, and
    ``text-embedding-3-large`` models.

    FLAGS:
        FAMILY:openai: Groups this model under the OpenAI family.
        remote: Marks this model as calling a remote API.
    """

    FLAGS: list[str] = ["FAMILY:openai", "remote"]
    DISPLAY_NAME = MultilingualString(
        en="OpenAI Embedding",
        es="Embedding OpenAI",
    )
    DESCRIPTION = MultilingualString(
        en="OpenAI text embeddings",
        es="Embeddings de texto de OpenAI",
    )
    SCHEMA = OpenAIEmbeddingSchema

    def __init__(self, **kwargs):
        """Initialise the embedding by validating parameters and creating the OpenAI client.

        Args:
            **kwargs: Configuration matching :class:`OpenAIEmbeddingSchema`.

        Raises:
            ValueError: If the API key is missing or empty.
        """  # noqa: E501
        self.params = self.validate_and_transform(kwargs)
        self.model_name = self.params["model_name"]
        self.api_key = self.params["api_key"]
        if not self.api_key or not self.api_key.strip():
            raise ValueError("OpenAI API key is required but was not provided")
        self.client = OpenAI(api_key=self.api_key)

    def load(self):
        """No-op. The OpenAI client does not require model loading."""

    def save(self):
        """No-op. No local state to persist."""

    def train(self, **kwargs):
        """No-op. OpenAI models cannot be fine-tuned through this interface."""

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text via the OpenAI API.

        Args:
            text: Input string.

        Returns:
            A 1-D float32 NumPy array of shape ``(embedding_dim,)``.
        """
        response = self.client.embeddings.create(
            model=self.model_name,
            input=_sanitize_input(text),
        )
        return np.array(response.data[0].embedding)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts via the OpenAI API.

        OpenAI limits the number of inputs per embeddings request, so
        large chunk sets are split into slices of at most
        ``OPENAI_MAX_INPUTS_PER_REQUEST`` and the results concatenated.
        OpenAI also rejects empty/whitespace-only inputs, so those are
        sanitized to a single space (the row count stays aligned with
        ``texts``).

        Args:
            texts: List of input strings.

        Returns:
            A ``(batch, embedding_dim)`` float32 NumPy array.
        """
        if not texts:
            return np.empty((0, 0))
        embeddings: List[np.ndarray] = []
        for start in range(0, len(texts), OPENAI_MAX_INPUTS_PER_REQUEST):
            slice_texts = texts[start : start + OPENAI_MAX_INPUTS_PER_REQUEST]
            sanitized = [_sanitize_input(t) for t in slice_texts]
            response = self.client.embeddings.create(
                model=self.model_name,
                input=sanitized,
            )
            embeddings.append(np.array([d.embedding for d in response.data]))
        return np.vstack(embeddings)
