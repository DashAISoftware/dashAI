from abc import abstractmethod
from typing import Any, List

import numpy as np

from DashAI.back.models.base_model import BaseModel


class DenseEmbedding(BaseModel):
    """
    Base class for all encoding (embedding) models.
    This class should be inherited by any specific encoding (embedding)
    model implementation.
    """

    embedding_dim: int

    def __init__(self, **kwargs: Any):
        """
        Initialize the encoding (embedding) model with the given documents.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")

    def encode(self, text: str) -> List[float] | np.ndarray:
        """
        Method to generate encodings (embeddings) for the given text.
        This method should be implemented by subclasses.

        :param text: The input text to encode (embed).
        :return: A list representing the encodings (embeddings) of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def batch_encode(self, texts: List[str]) -> List[List[float]] | np.ndarray:
        """
        Method to generate encodings (embeddings) for a batch of texts.
        This method should be implemented by subclasses.

        :param texts: A list of input texts to encode (embed).
        :return: A list of lists representing the encodings (embeddings)
            of the input texts.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def train(self, **kwargs):
        """Train the embedding model."""
        return
