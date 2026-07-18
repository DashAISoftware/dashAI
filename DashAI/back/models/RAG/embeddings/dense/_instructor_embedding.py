from typing import List

import numpy as np

try:
    from InstructorEmbedding import INSTRUCTOR
except ImportError as err:
    raise ImportError(
        "InstructorEmbedding package is not installed. "
        "Install it with: pip install InstructorEmbedding"
    ) from err

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)


class _InstructorEmbedding(HuggingFaceEmbedding):
    """Internal wrapper around the ``InstructorEmbedding`` package.

    Prepends a fixed instruction string to every input text and delegates
    encoding to the ``INSTRUCTOR`` model (which handles its own pooling).
    """

    def __init__(
        self,
        model_name: str,
        device: str,
        instruction: str,
    ):
        """Initialise the INSTRUCTOR embedding wrapper.

        Args:
            model_name: HuggingFace model identifier for the INSTRUCTOR model.
            device: Target device (ignored — INSTRUCTOR manages its own device).
            instruction: Instruction text prepended to every query / document.
        """
        super().__init__(model_name=model_name, device=device)
        self.instruction = instruction
        self.params["instruction"] = instruction

    def _pool(self, model_output, attention_mask):
        """Not implemented — INSTRUCTOR uses its own encoding API."""
        raise NotImplementedError(
            "INSTRUCTOR uses custom encoding API, _pool is unused."
        )

    def load(self):
        """Instantiate the ``INSTRUCTOR`` model from the ``InstructorEmbedding`` package."""  # noqa: E501
        self.model = INSTRUCTOR(self.model_name)
        self.model._text_length = self.model._input_length

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts with the fixed instruction prefix.

        Args:
            texts: List of input strings.

        Returns:
            A ``(batch, embedding_dim)`` float32 NumPy array.
        """
        pairs = [[self.instruction, text] for text in texts]
        return self.model.encode(pairs, show_progress_bar=False)

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text with the fixed instruction prefix.

        Args:
            text: Input string.

        Returns:
            A 1-D float32 NumPy array of shape ``(embedding_dim,)``.
        """
        result = self.model.encode([[self.instruction, text]], show_progress_bar=False)
        return result.squeeze()
