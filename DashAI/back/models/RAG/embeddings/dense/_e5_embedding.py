from typing import List

import numpy as np
import torch
import torch.nn.functional as F

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


class _E5Embedding(HuggingFaceEmbedding):
    def __init__(self, model_name: str, device: str, max_length: int):
        super().__init__(model_name=model_name, device=device)
        self.max_length = max_length
        self.params["max_length"] = max_length

    def _pool(self, model_output, attention_mask):
        last_hidden = model_output[0]
        mask = attention_mask[..., None].bool()
        last_hidden = last_hidden.masked_fill(~mask, 0.0)
        pooled = last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]
        return F.normalize(pooled, p=2, dim=1)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        prefixed = [f"{PASSAGE_PREFIX}{t}" for t in texts]
        return self._batch_encode_impl(prefixed)

    def encode(self, text: str) -> np.ndarray:
        result = self._batch_encode_impl([f"{QUERY_PREFIX}{text}"])
        return result.squeeze()
