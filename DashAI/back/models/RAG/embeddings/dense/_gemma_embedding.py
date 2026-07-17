from typing import List

import numpy as np

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)

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
    def __init__(
        self,
        model_name: str,
        device: str,
        model_max_length: int,
        overflow_strategy: str,
        task_type: str,
    ):
        super().__init__(model_name=model_name, device=device)
        self.model_max_length = model_max_length
        self.overflow_strategy = overflow_strategy
        self.task_type = task_type
        self.params["model_max_length"] = model_max_length
        self.params["overflow_strategy"] = overflow_strategy
        self.params["task_type"] = task_type

    def _pool(self, model_output, attention_mask):
        raise NotImplementedError(
            "Gemma uses SentenceTransformer API, _pool is unused."
        )

    def load(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(self.model_name, device=self.device)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        prompted = [DOCUMENT_PROMPT + t for t in texts]
        return self.model.encode(
            prompted, normalize_embeddings=True, show_progress_bar=False
        )

    def encode(self, text: str) -> np.ndarray:
        query_prompt = TASK_PROMPTS[self.task_type]
        return self.model.encode(
            [query_prompt + text], normalize_embeddings=True, show_progress_bar=False
        ).squeeze()
