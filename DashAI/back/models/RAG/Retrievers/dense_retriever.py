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

        self._documents_path = kwargs.get("documents_path")
        self.documents = kwargs.get("documents") 
        self.chunking_model = kwargs.get("chunking_model")
        self.encoding_model = kwargs.get("encoding_model")
        self.similarity_metric = kwargs.get("similarity_metric", "cosine")

        assert self._documents_path is not None, "Documents path must be provided."
        assert self.documents is not None and len(self.documents) > 0, "Documents must be provided and cannot be empty."
        assert self.validate_documents_in_folder(self.documents), "Some documents are missing from the folder."
        assert self.chunking_model is not None, "Chunking model must be provided."
        assert self.encoding_model is not None, "Encoding model must be provided."
        assert self.similarity_metric in ["cosine", "dot_product", "euclidean"], (
            f"Invalid similarity metric: {self.similarity_metric}. "
            "Choose from 'cosine', 'dot_product', or 'euclidean'."
        )
        assert self.n_docs > 0, "Number of documents must be greater than 0."

        print(f"DenseRetriever initialized with encoding model: {self.encoding_model} and similarity metric: {self.similarity_metric}")

    def load():
        """Load the dense retriever model."""
        print("Loading DenseRetriever model...")
        # Placeholder for loading logic
        pass

    def save():
        """Save the dense retriever model."""
        print("Saving DenseRetriever model...")
        # Placeholder for saving logic
        pass



