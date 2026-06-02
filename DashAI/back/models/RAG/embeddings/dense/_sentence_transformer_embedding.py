import torch
import torch.nn.functional as F

from DashAI.back.models.RAG.embeddings.dense._overflow_handler import (
    OverfloatHandler,
)

TRUNCATE = "truncate"
AGGREGATE = "aggregate"


class _SentenceTransformerEmbedding(OverfloatHandler):
    def __init__(
        self,
        model_name: str,
        device: str,
        model_max_length: int,
        overflow_strategy: str,
        normalize: bool,
    ):
        super().__init__(
            model_name=model_name,
            device=device,
            model_max_length=model_max_length,
            overflow_strategy=overflow_strategy,
        )
        self.normalize = normalize
        self.params["normalize"] = normalize

    def _pool(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        pooled = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )
        if self.normalize:
            pooled = F.normalize(pooled, p=2, dim=1)
        return pooled
