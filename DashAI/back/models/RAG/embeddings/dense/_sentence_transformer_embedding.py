import torch
import torch.nn.functional as functional

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
        pooling: str = "mean",
    ):
        super().__init__(
            model_name=model_name,
            device=device,
            model_max_length=model_max_length,
            overflow_strategy=overflow_strategy,
        )
        self.normalize = normalize
        self.pooling = pooling
        self.params["normalize"] = normalize
        self.params["pooling"] = pooling

    def _pool(self, model_output, attention_mask):
        if self.pooling == "last_token":
            return self._last_token_pool(model_output, attention_mask)
        token_embeddings = model_output[0]
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        pooled = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )
        if self.normalize:
            pooled = functional.normalize(pooled, p=2, dim=1)
        return pooled

    def _last_token_pool(self, model_output, attention_mask):
        last_hidden_states = model_output[0]
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            pooled = last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            pooled = last_hidden_states[
                torch.arange(batch_size, device=last_hidden_states.device),
                sequence_lengths,
            ]
        if self.normalize:
            pooled = functional.normalize(pooled, p=2, dim=1)
        return pooled
