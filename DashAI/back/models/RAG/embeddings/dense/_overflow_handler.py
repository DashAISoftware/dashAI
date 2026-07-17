from abc import abstractmethod
from typing import List

import numpy as np
import torch

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)

TRUNCATE = "truncate"
AGGREGATE = "aggregate"


class OverfloatHandler(HuggingFaceEmbedding):
    def __init__(
        self,
        model_name: str,
        device: str,
        model_max_length: int,
        overflow_strategy: str,
    ):
        super().__init__(model_name=model_name, device=device)
        self.model_max_length = model_max_length
        self.overflow_strategy = overflow_strategy
        self.params["model_max_length"] = model_max_length
        self.params["overflow_strategy"] = overflow_strategy

    @abstractmethod
    def _pool(self, model_output, attention_mask):
        raise NotImplementedError

    def _batch_encode_impl(self, texts: List[str]) -> np.ndarray:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.model_max_length,
            return_tensors="pt",
            return_overflowing_tokens=self.overflow_strategy == AGGREGATE,
            stride=0,
        )
        num_texts = len(texts)
        if self.overflow_strategy not in [TRUNCATE, AGGREGATE]:
            raise ValueError(
                f"Invalid overflow strategy: {self.overflow_strategy}. "
                f"Supported strategies are: {TRUNCATE}, {AGGREGATE}."
            )
        if (
            self.overflow_strategy == AGGREGATE
            and "overflow_to_sample_mapping" in encoded
        ):
            mapping = encoded.pop("overflow_to_sample_mapping")
            encoded = {k: v.to(self.device) for k, v in encoded.items()}
            with torch.no_grad():
                outputs = self.model(**encoded)
            segment_embeddings = self._pool(outputs, encoded["attention_mask"]).cpu()
            result = []
            for i in range(num_texts):
                segment_indices = (mapping == i).nonzero(as_tuple=True)[0]
                if len(segment_indices) == 1:
                    result.append(segment_embeddings[segment_indices[0]])
                else:
                    result.append(
                        torch.mean(segment_embeddings[segment_indices], dim=0)
                    )
            return torch.stack(result).numpy()
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        with torch.no_grad():
            outputs = self.model(**encoded)
        embeddings = self._pool(outputs, encoded["attention_mask"])
        return embeddings.cpu().numpy()
