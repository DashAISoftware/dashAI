from typing import List

import numpy as np

from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)


class _InstructorEmbedding(HuggingFaceEmbedding):
    def __init__(
        self,
        model_name: str,
        device: str,
        instruction: str,
    ):
        super().__init__(model_name=model_name, device=device)
        self.instruction = instruction
        self.params["instruction"] = instruction

    def _pool(self, model_output, attention_mask):
        raise NotImplementedError(
            "INSTRUCTOR uses custom encoding API, _pool is unused."
        )

    def load(self):
        from InstructorEmbedding import INSTRUCTOR

        self.model = INSTRUCTOR(self.model_name)
        self.model._text_length = self.model._input_length

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        pairs = [[self.instruction, text] for text in texts]
        return self.model.encode(pairs, show_progress_bar=False)

    def encode(self, text: str) -> np.ndarray:
        result = self.model.encode([[self.instruction, text]], show_progress_bar=False)
        return result.squeeze()
