import torch
import torch.nn.functional as F

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)


class _SentenceTransformerEmbedding(HuggingFaceEmbedding):
    def __init__(self, model_name: str, device: str, max_length: int):
        super().__init__(model_name=model_name, device=device)
        self.max_length = max_length
        self.params["max_length"] = max_length

    def _pool(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        pooled = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )
        return F.normalize(pooled, p=2, dim=1)
