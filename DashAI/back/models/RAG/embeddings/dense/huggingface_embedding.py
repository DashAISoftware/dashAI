from transformers import AutoModel


from DashAI.back.core.schema_fields import (
    BaseSchema,
    schema_field,
    enum_field
)
from typing import Final, List
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from DashAI.back.models.RAG.embeddings.dense_encoding import DenseEmbedding
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class HuggingFaceEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(
            [
                # Sentence Transformers Models
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "sentence-transformers/all-distilroberta-v1",
                # BERT Models
                "bert-base-uncased",
                "bert-large-uncased",
                "bert-base-multilingual-cased",
                "distilbert-base-uncased",
                # RoBERTa Models
                "roberta-base",
                "roberta-large",
                "distilroberta-base",
            ]
        ),
        "sentence-transformers/all-MiniLM-L6-v2",
        "Name of the pre-trained model to use",
    )  # type: ignore

    max_length: schema_field(
        int_field(ge=1), 512, "Maximum sequence length for tokenization"
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1), 32, "Number of samples to process at once"
    )  # type: ignore

    device: schema_field(
        enum_field(["cuda", "cpu"]),
        "cpu",
        "Device to use for computation",
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(["mean", "cls", "max"]),
        "mean",
        "Strategy to pool token embeddings into sentence embedding",
    )  # type: ignore


class HuggingFaceEmbedding(DenseEmbedding):
    """HuggingFace embedding"""

    SCHEMA = HuggingFaceEmbeddingSchema
    DESCRIPTION = "Convert text to embeddings using HuggingFace transformer models."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pooling_strategy = kwargs.get("pooling_strategy", "mean")
        self.model_name = kwargs.get(
            "model_name", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.device = kwargs.get("device", "cpu")
        self.max_length = kwargs.get("max_length", 512)
        self.batch_size = kwargs.get("batch_size", 32)
        self.model = None
        self.tokenizer = None

    def _load_model(self):
        """Load the embedding model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()

    def _encode_texts(self, texts:List[str])-> List[np.ndarray]:
        """Encode a list of texts into embeddings."""
        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**encoded)
            hidden_states = outputs.last_hidden_state

            # Apply pooling strategy
            if self.pooling_strategy == "mean":
                embeddings = torch.mean(hidden_states, dim=1)
            elif self.pooling_strategy == "cls":
                embeddings = hidden_states[:, 0]
            else:  # max pooling
                embeddings = torch.max(hidden_states, dim=1)[0]

        embeddings_np = embeddings.cpu().numpy()
        return embeddings_np

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into an embedding."""
        embeddings = self._encode_texts([text])
        return embeddings[0] if embeddings else np.array([])
