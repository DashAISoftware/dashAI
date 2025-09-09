
from typing import List

import numpy as np
from DashAI.back.core.schema_fields import enum_field
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.models.RAG.encodings.dense_encoding import DenseEncoding

import fasttext
from huggingface_hub import hf_hub_download

class FastTextEmbeddingSchema(DenseEncoding.SCHEMA):
    model_name: schema_field(
        enum_field(
            [
                "facebook/fasttext-es-vectors",
                "facebook/fasttext-en-vectors"
            ]
        ),
        "facebook/fasttext-en-vectors",
        "Name of the pre-trained model to use",
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(
            [
                "mean",
                "max"
            ]
        ),
        "mean",
        "Pooling strategy to use",
    )  # type: ignore

class FastTextEmbedding(DenseEncoding):
    """FastText embedding"""

    SCHEMA = FastTextEmbeddingSchema
    DESCRIPTION = "Convert text to embeddings using FastText."

    def __init__(self, **kwargs):
        self.validate_and_transform(**kwargs)
        self.model_name = kwargs.get("model_name")
        self.pooling_strategy = kwargs.get("pooling_strategy")
        pooling_functions = {
            "mean": np.mean,
            "max": np.max
        }
        self.pooling_function = pooling_functions[self.pooling_strategy]

    def _load_model(self):
        """Load the FastText model."""
        model_name = self.model_name.split("/")[-1]
        model_path = hf_hub_download(repo_id=self.model_name, filename=f"{model_name}.bin")
        self.model = fasttext.load_model(model_path)

    def encode(self, text: str) -> np.ndarray:
        """Encode text into an embedding."""
        token_embeddings = [self.model.get_word_vector(word) for word in text.split()]
        return self.pooling_function(np.array(token_embeddings), axis=0)
    