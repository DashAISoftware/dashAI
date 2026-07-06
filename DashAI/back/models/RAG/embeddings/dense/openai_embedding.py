from typing import List

import numpy as np
from openai import OpenAI

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.schema_fields.enum_field import enum_field
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.core.schema_fields.string_field import string_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding


class OpenAIEmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]),
        placeholder="text-embedding-3-small",
        description=MultilingualString(
            en="OpenAI embedding model to use.",
            es="Modelo de embedding de OpenAI a utilizar.",
        ),
    )  # type: ignore

    api_key: schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en="OpenAI API key.",
            es="Clave API de OpenAI.",
        ),
    )  # type: ignore


class OpenAIEmbedding(DenseEmbedding):
    FLAGS: list[str] = ["FAMILY:openai", "remote"]
    DISPLAY_NAME = MultilingualString(
        en="OpenAI Embedding",
        es="Embedding OpenAI",
    )
    DESCRIPTION = MultilingualString(
        en="OpenAI text embeddings",
        es="Embeddings de texto de OpenAI",
    )
    SCHEMA = OpenAIEmbeddingSchema

    def __init__(self, **kwargs):
        self.params = self.validate_and_transform(kwargs)
        self.model_name = self.params["model_name"]
        self.api_key = self.params["api_key"]
        self.client = OpenAI(api_key=self.api_key)

    def load(self):
        pass

    def save(self):
        pass

    def train(self, **kwargs):
        return

    def encode(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text,
        )
        return np.array(response.data[0].embedding)

    def batch_encode(self, texts: List[str]) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return np.array([d.embedding for d in response.data])
