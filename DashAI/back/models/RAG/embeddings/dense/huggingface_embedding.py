from abc import abstractmethod
from typing import List

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding


class HuggingFaceEmbedding(DenseEmbedding):
    FLAGS: list[str] = ["abstract", "huggingface"]

    def __init__(self, model_name: str, device: str):
        self.model_name = model_name
        self.device = device
        self.params = {
            "model_name": model_name,
            "device": device,
        }
        self.model = None
        self.tokenizer = None

    def save(self):
        pass

    def train(self, **kwargs):
        return

    @abstractmethod
    def _pool(self, model_output, attention_mask):
        raise NotImplementedError

    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)

    def _batch_encode_impl(self, texts: List[str]) -> np.ndarray:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        with torch.no_grad():
            outputs = self.model(**encoded)
        embeddings = self._pool(outputs, encoded["attention_mask"])
        return embeddings.cpu().numpy()

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        return self._batch_encode_impl(texts)

    def encode(self, text: str) -> np.ndarray:
        embeddings = self.batch_encode([text])
        return embeddings.squeeze()
