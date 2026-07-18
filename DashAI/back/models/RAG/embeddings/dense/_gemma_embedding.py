from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)
from DashAI.back.models.RAG.exceptions import RAGEmbeddingError

TASK_PROMPTS = {
    "search_result": "task: search result | query: ",
    "question_answering": "task: question answering | query: ",
    "fact_checking": "task: fact checking | query: ",
    "classification": "task: classification | query: ",
    "clustering": "task: clustering | query: ",
    "sentence_similarity": "task: sentence similarity | query: ",
    "code_retrieval": "task: code retrieval | query: ",
}

DOCUMENT_PROMPT = "title: none | text: "


class _GemmaEmbedding(HuggingFaceEmbedding):
    """Internal wrapper around Gemma embedding models via SentenceTransformers.

    Uses task-specific query prompts (from :data:`TASK_PROMPTS`) for
    encoding queries and a fixed document prompt for passages.
    """

    def __init__(
        self,
        model_name: str,
        device: str,
        model_max_length: int,
        overflow_strategy: str,
        task_type: str,
    ):
        """Initialise the Gemma embedding wrapper.

        Args:
            model_name: HuggingFace model identifier.
            device: Target device (``"cpu"`` or ``"cuda"``).
            model_max_length: Maximum token length.
            overflow_strategy: ``"truncate"`` or ``"aggregate"``.
            task_type: Prompt template key from :data:`TASK_PROMPTS`.
        """
        super().__init__(model_name=model_name, device=device)
        self.model_max_length = model_max_length
        self.overflow_strategy = overflow_strategy
        self.task_type = task_type
        self.params["model_max_length"] = model_max_length
        self.params["overflow_strategy"] = overflow_strategy
        self.params["task_type"] = task_type

    def _pool(self, model_output, attention_mask):
        """Not implemented — Gemma uses SentenceTransformer API directly."""
        raise NotImplementedError(
            "Gemma uses SentenceTransformer API, _pool is unused."
        )

    def load(self):
        """Load the Gemma model via ``SentenceTransformer``."""
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of documents with the fixed document prompt.

        Args:
            texts: List of input strings.

        Returns:
            A ``(batch, embedding_dim)`` float32 NumPy array.

        Raises:
            RAGEmbeddingError: If the model has not been loaded yet.
        """
        if self.model is None:
            raise RAGEmbeddingError(
                "Model not loaded. Call load() before batch_encode()."
            )
        prompted = [DOCUMENT_PROMPT + t for t in texts]
        return self.model.encode(
            prompted, normalize_embeddings=True, show_progress_bar=False
        )

    def encode(self, text: str) -> np.ndarray:
        """Encode a single query with the task-specific prompt.

        Args:
            text: Input string.

        Returns:
            A 1-D float32 NumPy array of shape ``(embedding_dim,)``.

        Raises:
            RAGEmbeddingError: If the model has not been loaded yet.
        """
        if self.model is None:
            raise RAGEmbeddingError("Model not loaded. Call load() before encode().")
        query_prompt = TASK_PROMPTS[self.task_type]
        return self.model.encode(
            [query_prompt + text], normalize_embeddings=True, show_progress_bar=False
        ).squeeze()
