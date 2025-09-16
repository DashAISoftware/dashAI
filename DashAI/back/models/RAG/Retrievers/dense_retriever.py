from .retriever_model import RetrieverModel

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    schema_field,
    enum_field
)
""" chunking_model: schema_field(
    component_field(
        parent="ChunkingModel"
        ),
    placeholder={"component": "Perico", "params": {}},
    description="Chunking model to split documents into smaller parts."
)# type: ignore """

class DenseRetrieverSchema(BaseSchema):
    """Schema for Dense Retriever."""

    encoding_model: schema_field(
        component_field(
            parent="DenseEmbedding"
        ),
        placeholder={"component": "Embedding", "params": {}},
        description="Model to convert text into dense vector representations."
    ) # type: ignore

    similarity_metric: schema_field(
        enum_field(
            enum=["cosine", "dot_product", "euclidean"]
        ),
        placeholder="cosine",
        description="Similarity metric to use for comparing dense vectors.",
    ) # type: ignore


class DenseRetriever(RetrieverModel):
    """
    Dense retriever class for retrieving documents based on dense vector representations.
    This class is a placeholder and should be implemented with specific dense retrieval logic.
    """

    SCHEMA = DenseRetrieverSchema

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chunking_model = kwargs.get("chunking_model")
        self.encoding_model = kwargs.get("encoding_model")

