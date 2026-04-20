from abc import ABC, abstractmethod
import os
from typing import Any, Dict, List, Final
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.documents import BaseDocument, PDFDocument, TxtDocument, Chunk
from DashAI.back.dependencies.database.models import(
    Document as DocumentDBModel,
    Chunk as ChunkDBModel,
    RAGRetriever as RetrieverDBModel,
    RAGPipeline as PipelineDBModel,
)
from DashAI.back.models.RAG.exceptions import RAGWorkflowError
from DashAI.back.models.RAG.utils import hash_function
from sqlalchemy.orm import Session

from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.RAG.extra_args_enum import (
    PIPELINE_ID,
    DB,
    COMPONENT_REGISTRY,
    ENV_RAG_PATH,
    DOCUMENTS,
    CHUNKS,
    CHUNKING_MODEL_ID
)

class RetrieverModel(BaseModel):
    """
    Abstract class to define the interface for retriever models.
    """

    REQUIRED_EXTRA_KWARGS: Final[List[str]] = [PIPELINE_ID, DB, COMPONENT_REGISTRY, ENV_RAG_PATH, DOCUMENTS, CHUNKS, CHUNKING_MODEL_ID]

    id: int
    pipeline_id: int
    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str|os.PathLike

    documents: Dict[int, BaseDocument]
    chunks: Dict[int, Dict[int, Chunk]]
    chunking_model_id: int

    retriever_db_model = RetrieverDBModel
    class_name: str
    params: Dict[str, Any]
    
    def __init__(self, **kwargs):
        self.class_name = kwargs.pop("class_name")
        self.params = kwargs
        self.pipeline_id: int = self.params.pop("pipeline_id")
        self.db: Session = self.params.pop("db")
        self.component_registry: ComponentRegistry = self.params.pop("component_registry")
        self.env_rag_path: str|os.PathLike = self.params.pop("env_rag_path")
        self.documents: Dict[int, BaseDocument] = self.params.pop("documents")
        self.chunks: Dict[int, Dict[int, Chunk]] = self.params.pop("chunks")
        self.chunking_model_id: int = self.params.pop("chunking_model_id")
        self.validate_chunks()
        self.params = self.validate_and_transform(self.params)


        if self.pipeline_id is not None:
            existing_pipeline: PipelineDBModel = self.db.query(PipelineDBModel).filter(
                PipelineDBModel.id == self.pipeline_id
            ).first()
            self.retriever_db_model = self.db.query(RetrieverDBModel).filter(
                RetrieverDBModel.id == existing_pipeline.retriever_model_id
            ).first()
            assert self.retriever_db_model is not None, "Retriever model not found in the database, but pipeline exists."
        else:
            self.pipeline_id = None
            self.retriever_db_model = None

    def validate_chunks(self) -> None:
        """Validate the structure and content of the chunks dictionary."""
        if not isinstance(self.chunks, dict):
            raise ValueError("Chunks must be a dictionary.")
        for doc_id, doc_chunks in self.chunks.items():
            if not isinstance(doc_id, int):
                raise ValueError(f"Document ID {doc_id} must be an integer.")
            if not isinstance(doc_chunks, dict):
                raise ValueError(f"Chunks for document ID {doc_id} must be a dictionary.")
            for chunk_id, chunk in doc_chunks.items():
                if not isinstance(chunk_id, int):
                    raise ValueError(f"Chunk ID {chunk_id} in document ID {doc_id} must be an integer.")
                if not isinstance(chunk, Chunk):
                    raise ValueError(f"Chunk {chunk_id} in document ID {doc_id} must be an instance of Chunk.")
                assert chunk.document_id == doc_id, f"Chunk {chunk_id} doc_id {chunk.doc_id} does not match document ID {doc_id}."

        
    @abstractmethod
    def retrieve(self, **kwargs) -> List[Chunk]:
        """
        Retrieve documents based on the provided parameters.
        
        Args:
            **kwargs: The parameters for the retrieval.
        
        Returns:
            List[BaseDocument]: A list of retrieved documents.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
        
    def init_retriever_db_model(self, dense_retriver_db_id: int, sparse_retriver_db_id: int) -> RetrieverDBModel:
        """Initialize the retriever model in the database."""
        assert dense_retriver_db_id or sparse_retriver_db_id, "At least one of dense_retriver_db_id or sparse_retriver_db_id must be provided."
        class_name = self.__class__.__name__
        retriever_db_model = RetrieverDBModel(
            class_name=class_name,
            dense_retriever_id=dense_retriver_db_id,
            sparse_retriever_id=sparse_retriver_db_id,
        )
        self.db.add(retriever_db_model)
        self.db.commit()

    def load(self):
        pass

    def save(self):
        pass
    
    def get_id(self) -> int:
        """Get the ID of the retriever model from the database."""
        return self.retriever_db_model.id
    
    def set_id(self, id: int) -> None:
        """Set the ID of the retriever model in the database."""
        if self.id is None:
            self.id = id
        else:
            raise RAGWorkflowError("ID is already set and cannot be modified.")
        
    def train(self, **kwargs):
        """Train the retriever model."""
        return