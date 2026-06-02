from typing import List

import numpy as np

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)


class _GemmaEmbedding(HuggingFaceEmbedding):
    def __init__(self, model_name: str, device: str, max_length: int):
        super().__init__(model_name=model_name, device=device)
        self.max_length = max_length
        self.params["max_length"] = max_length

    def _pool(self, model_output, attention_mask):
        raise NotImplementedError("Gemma uses SentenceTransformer API, _pool is unused.")

    def load(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    def encode(self, text: str) -> np.ndarray:
        return self.model.encode([text], normalize_embeddings=True).squeeze()
