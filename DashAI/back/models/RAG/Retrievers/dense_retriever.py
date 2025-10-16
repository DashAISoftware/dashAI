import os
from typing import Dict, List
import numpy as np
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    enum_field,
    schema_field,
    int_field
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.dependencies.database.models import (
    RAGEmbeddingMatrix as EmbeddingMatrixDBModel,
    RAGEmbeddingModel as EmbeddingDBModel,
    RAGDenseRetriever as DenseRetrieverDBModel,
    RAGRetriever as RetrieverDBModel,
    RAGPipeline as PipelineDBModel,
)
from DashAI.back.models.RAG.documents import BaseDocument, Chunk
from DashAI.back.models.RAG.Retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.embeddings.dense import FastTextEmbedding, HuggingFaceEmbedding
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

class DenseRetrieverSchema(BaseSchema):
    """Schema for Dense Retriever."""

    encoding_model: schema_field(
        component_field(parent="DenseEmbedding"),
        placeholder={"component": "FastTextEmbedding", "params": {}},
        description="Model to convert text into dense vector representations.",
    )  # type: ignore

    similarity_metric: schema_field(
        enum_field(enum=[
            "cityblock", "cosine", "euclidean", "l1", "l2", "manhattan", "nan_euclidean",
            "braycurtis", "canberra", "chebyshev", "correlation", "dice", "hamming", "jaccard", 
            "mahalanobis", "minkowski", "rogerstanimoto", "russellrao", "seuclidean", 
            "sokalmichener", "sokalsneath", "sqeuclidean", "yule"
            ]),
        placeholder="cosine",
        description="Distance metric to use for comparing dense vectors. For reference see https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise_distances.html#sklearn.metrics.pairwise_distances",
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description="Number of top documents to retrieve."
    )  # type: ignore


class DenseRetriever(RetrieverModel):
    """
    Dense retriever class for retrieving documents based on dense vector
    representations.
    """

    SCHEMA = DenseRetrieverSchema

    pipeline_id: int
    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str|os.PathLike

    documents: Dict[int, BaseDocument]
    chunks: Dict[int, Dict[int, Chunk]]
    chunking_model_id: int

    id: int
    retriever_db_model = RetrieverDBModel
    dense_retriever_db_model: DenseRetrieverDBModel
    embedding_model: DenseEmbedding
    embedding_db_model: EmbeddingDBModel
    embedding_db_matrices: Dict[int, EmbeddingMatrixDBModel]

    matrix_row_to_chunk_id: Dict[int, int]
    chunk_id_to_doc_id: Dict[int, int]

    def __init__(self, **kwargs):
        # RetrieverModel class fetches retriever_db_model if exists
        super().__init__(**kwargs)

        embedding_args = self.params["encoding_model"]["properties"]["params"]["comp"]
        self.embedding_class_name = embedding_args["component"]
        self.embedding_params = embedding_args.get("params", {})
        embedding_class = self.component_registry[self.embedding_class_name]["class"]
        self.embedding_model: DenseEmbedding = embedding_class(**self.embedding_params)

        #self.embedding_model: DenseEmbedding = self.params["encoding_model"]
        #self.embedding_class_name = self.embedding_model.__class__.__name__
        #self.embedding_params = self.embedding_model.params
       
        self.fetch_db_models()
        self.similarity_metric = self.params["similarity_metric"]
        self.top_k = self.params["top_k"]

        if self.embedding_db_model is None:
            self.embedding_db_model = self.create_embedding_db_model()
        self.compute_missing_embeddings()
        if not self.dense_retriever_db_model:
            db_model = DenseRetrieverDBModel(
                class_name=self.__class__.__name__,
                parameters=self.params,
                embedding_model_id=self.embedding_db_model.id
            ) 
            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)
            self.dense_retriever_db_model = db_model
        if not self.retriever_db_model:
            retriever_db_model = RetrieverDBModel(
                class_name=self.__class__.__name__,
                dense_retriever_id=self.dense_retriever_db_model.id,
                sparse_retriever_id=None
            )
            self.db.add(retriever_db_model)
            self.db.commit()
            self.db.refresh(retriever_db_model)
            self.retriever_db_model = retriever_db_model

        self.init_similarity_matrix()

    def __fetch_embedding_db_model(self)-> EmbeddingDBModel|None:
        """Fetch the embedding database model if it exists."""
        embedding_db_model = self.db.query(EmbeddingDBModel).filter_by(
            class_name=self.embedding_class_name,
            parameters=self.embedding_params
        ).first()
        return embedding_db_model

    def fetch_db_models(self):
        """Fetch all database models related to the retriever if they exist."""
        self.embedding_db_model = self.__fetch_embedding_db_model()

        self.embedding_db_matrices = {}
        if self.embedding_db_model and self.chunking_model_id:
            self.embedding_db_matrices = self.fetch_embedding_matrices()

        self.retriever_db_model = None
        self.dense_retriever_db_model = None
        if self.pipeline_id:
            pipeline_model = self.db.query(PipelineDBModel).filter_by(
                id=self.pipeline_id).first()
            retriever_id = pipeline_model.retriever_model_id
            self.retriever_db_model = self.db.query(RetrieverDBModel).filter_by(
                id=retriever_id).first()
            dense_retriever_id = self.retriever_db_model.dense_retriever_id
            self.dense_retriever_db_model = self.db.query(DenseRetrieverDBModel).filter_by(
                id=dense_retriever_id).first()

    def fetch_embedding_matrices(self) -> Dict[int, EmbeddingMatrixDBModel]:
        """Load precomputed embeddings from the database if they exist."""
        embeddings_matrices_db_models = {}
        for doc_id, doc_chunks in self.chunks.items():
            embedding_matrix_entry = (
                self.db.query(EmbeddingMatrixDBModel)
                .filter_by(
                    document_id=doc_id, 
                    chunking_model_id=self.chunking_model_id,
                    embedding_model_id=self.embedding_db_model.id
                ).first()
            )
            if embedding_matrix_entry:
                embeddings_matrices_db_models[doc_id] = embedding_matrix_entry

        return embeddings_matrices_db_models

    def create_embedding_db_model(self) -> EmbeddingDBModel:
        """Create the embedding model in the database."""
        new_model = EmbeddingDBModel(
            class_name=self.embedding_class_name,
            parameters=self.embedding_params
        )
        self.db.add(new_model)
        self.db.commit()
        self.db.refresh(new_model)
        return new_model

    def save(self):
        """Save the dense retriever model to the database."""
        pass      

    def compute_missing_embeddings(self):
        chunking_model_id = self.chunking_model_id
        embedding_model_id = self.embedding_db_model.id
        assert embedding_model_id and chunking_model_id, "Embedding model ID and chunking model ID must be set to compute embeddings."
        for doc_id, doc_chunks in self.chunks.items():
            db_model = self.embedding_db_matrices.get(doc_id, None)
            if db_model:
                print(f"Embeddings for document {doc_id} already exist in the database ({db_model}). Skipping computation.")
                continue
            chunk_texts = [chunk.text for chunk in doc_chunks.values()]
            embeddings = self.embedding_model.batch_encode(chunk_texts)
            matrix_shape = embeddings.shape
            folder_name = f"doc_id-{doc_id}__chunking_model_id-{chunking_model_id}__embedding_model_id-{embedding_model_id}"
            storage_folder = os.path.join(self.env_rag_path, "embeddings", folder_name)
            os.makedirs(storage_folder, exist_ok=True)
            file_path = os.path.join(storage_folder, "embeddings.npy")
            np.save(file_path, embeddings)
            new_db_model = EmbeddingMatrixDBModel(
                document_id=doc_id,
                chunking_model_id=chunking_model_id,
                embedding_model_id=embedding_model_id,
                matrix_shape=list(matrix_shape),
                storage_folder=storage_folder
            )
            self.db.add(new_db_model)
            self.db.commit()
            self.db.refresh(new_db_model)
            self.embedding_db_matrices[doc_id] = new_db_model

    def init_similarity_matrix(self):
        """Initialize the similarity matrix for all chunks."""
        self.similarity_matrix = None
        self.matrix_row_to_chunk_id = {}
        self.chunk_id_to_doc_id = {}  # Initialize the missing dictionary
        if not self.embedding_db_matrices:
            import warnings
            warnings.warn("No embedding matrices found to initialize similarity matrix.")
            return
        all_embeddings = []
        row_index = 0
        for doc_id, chunks in self.chunks.items():
            matrix_db_model = self.embedding_db_matrices[doc_id]
            matrix_folder = matrix_db_model.storage_folder
            matrix_path = os.path.join(matrix_folder, "embeddings.npy")
            assert os.path.exists(matrix_path), f"Embedding matrix file not found at {matrix_path}"
            for chunk_id, chunk in chunks.items():
                self.matrix_row_to_chunk_id[row_index] = chunk_id
                self.chunk_id_to_doc_id[chunk_id] = doc_id
                row_index += 1
            embeddings = np.load(matrix_path)
            all_embeddings.append(embeddings)
        self.similarity_matrix = np.vstack(all_embeddings)

    def retrieve(self, query: str) -> List[Chunk]:
        """Retrieve the top_k most similar chunks to the query."""
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not initialized.")
        query_embedding = self.embedding_model.encode(query)
        # Get distances and indices for all chunks
        distances = pairwise_distances(
            query_embedding.reshape(1, -1), 
            self.similarity_matrix, 
            metric=self.similarity_metric
        )[0]

        top_indices = np.argsort(distances)[:self.top_k]

        results = []
        for idx in top_indices:
            chunk_id = self.matrix_row_to_chunk_id[idx]
            doc_id = self.chunk_id_to_doc_id[chunk_id]
            chunk = self.chunks[doc_id][chunk_id]
            results.append(chunk)
        return results
            