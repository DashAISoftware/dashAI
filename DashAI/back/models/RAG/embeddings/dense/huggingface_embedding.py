from typing import List

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
    bool_field
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding


class HuggingFaceEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(
            [
                # Sentence Transformers Models
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "sentence-transformers/all-distilroberta-v1",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                "sentence-transformers/distiluse-base-multilingual-cased-v2",
                "sentence-transformers/distiluse-base-multilingual-cased-v1"
                # BERT Models
                "google-bert/bert-base-cased",
                "google-bert/bert-base-uncased",
                "google-bert/bert-large-cased",
                "google-bert/bert-large-uncased",
                "google-bert/bert-base-multilingual-cased",
                "google-bert/bert-base-multilingual-uncased",
                # DistilBERT Models
                "distilbert/distilbert-base-cased",
                "distilbert/distilbert-base-uncased",
                "distilbert/distilbert-roberta-base",
                "distilbert/distilbert-base-multilingual-cased",
                "distilbert/distilgpt2"
                # RoBERTa Models
                "FacebookAI/roberta-base",
                "FacebookAI/roberta-large",
                "FacebookAI/xlm-roberta-base",
                "FacebookAI/xlm-roberta-large"
                # Gemma Models
                "google/embeddinggemma-300m"
                # Intfloat Models
                "intfloat/e5-small-v2",
                "intfloat/e5-small-v2",
                "intfloat/e5-large-v2",
                
            ]
        ),
        "sentence-transformers/all-MiniLM-L6-v2",
        "Name of the pre-trained model to use",
    )  # type: ignore

    padding: schema_field(
        bool_field(),
        True,
        "Whether to pad sequences to the same length",
    )  # type: ignore

    truncation: schema_field(
        bool_field(),
        True,
        "Whether to truncate sequences that exceed the maximum length",
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(["mean", "cls", "max"]),
        "mean",
        "Pooling strategy to apply to the token embeddings",
    )  # type: ignore

    normalize: schema_field(
        bool_field(),
        True,
        "Whether to normalize the resulting embeddings to unit length",
    )  # type: ignore

    device: schema_field(
        enum_field(["cuda", "cpu"]),
        "cpu",
        "Device to use for computation",
    )  # type: ignore

class HuggingFaceEmbedding(DenseEmbedding):
    """HuggingFace embedding"""

    SCHEMA = HuggingFaceEmbeddingSchema
    DESCRIPTION = "Convert text to embeddings using HuggingFace transformer models."

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        self.model_name = self.params["model_name"]
        self.device = self.params["device"]
        self.padding = self.params["padding"]
        self.truncation = self.params["truncation"]
        self.pooling_strategy = self.params["pooling_strategy"]
        self.normalize = self.params["normalize"]
        self.model = None
        self.tokenizer = None
        self.load()

    def save(self):
        pass

    def train(self, **kwargs):
        return

    def load(self):
        """Load the embedding model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)

    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0] #First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def cls_pooling(self, model_output):
        return model_output[0][:, 0] #First token ([CLS]) of the output
    
    def max_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0] #First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        token_embeddings[input_mask_expanded == 0] = -1e9 #Set padding tokens to a very small value
        return torch.max(token_embeddings, 1)[0]

    def batch_encode(self, texts: List[str]) -> List[np.ndarray]:

        """Encode a list of texts into embeddings."""
        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=self.padding,
            truncation=self.truncation,
            return_tensors="pt",
        )

        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**encoded)
        if self.pooling_strategy == "mean":
            embeddings = self.mean_pooling(outputs, encoded["attention_mask"])
        elif self.pooling_strategy == "cls":
            embeddings = self.cls_pooling(outputs)
        elif self.pooling_strategy == "max":
            embeddings = self.max_pooling(outputs, encoded["attention_mask"])
        else:
            raise ValueError(f"Unsupported pooling strategy: {self.pooling_strategy}")
        if self.normalize:
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.cpu().numpy()
    

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into an embedding."""
        embeddings = self.batch_encode([text])
        return embeddings.squeeze()
