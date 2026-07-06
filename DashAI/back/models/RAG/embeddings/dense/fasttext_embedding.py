from typing import List

import fasttext
import numpy as np
from huggingface_hub import hf_hub_download

from DashAI.back.core.schema_fields import enum_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding


class FastTextEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(["facebook/fasttext-es-vectors", "facebook/fasttext-en-vectors"]),
        "facebook/fasttext-en-vectors",
        "Name of the pre-trained model to use",
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(["mean", "max"]),
        "mean",
        "Pooling strategy to use",
    )  # type: ignore


class FastTextEmbedding(DenseEmbedding):
    """FastText embedding"""

    FLAGS: list[str] = ["FAMILY:fasttext"]
    SCHEMA = FastTextEmbeddingSchema
    DISPLAY_NAME = MultilingualString(
        en="FastText Embedding",
        es="Embedding FastText",
    )
    DESCRIPTION = MultilingualString(
        en="Convert text to embeddings using FastText.",
        es="Convierte texto a embeddings usando FastText.",
    )

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        self.model_name = self.params["model_name"]
        self.pooling_strategy = self.params["pooling_strategy"]
        pooling_functions = {"mean": np.mean, "max": np.max}
        self.pooling_function = pooling_functions[self.pooling_strategy]
        self.model = None

    def load(self):
        """Load the FastText model."""
        if self.model is not None:
            return
        model_path = hf_hub_download(repo_id=self.model_name, filename="model.bin")
        self.model = fasttext.load_model(model_path)

    def save(self):
        pass

    def train(self, **kwargs):
        pass

    def encode(self, text: str) -> np.ndarray:
        """Encode text into an embedding."""
        token_embeddings = [self.model.get_word_vector(word) for word in text.split()]
        return self.pooling_function(np.array(token_embeddings), axis=0)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into embeddings."""
        all_embeddings = []
        for text in texts:
            embedding = self.encode(text)
            all_embeddings.append(embedding)
        return np.array(all_embeddings)
