from abc import ABCMeta, abstractmethod
from DashAI.back.config_object import ConfigObject
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.dependencies.database.models import (
    RAGChunkingModel as DBChunkingModel,
    Chunk as DBChunkModel,
    RAGPipeline as PipelineDBModel,
)
from typing import Any, Dict, Final, List
from sqlalchemy.orm import Session
from DashAI.back.models.RAG.utils import hash_function

class BaseChunkingModel(ConfigObject, metaclass=ABCMeta):
    """
    Base class for chunking models.
    This class should be inherited by any specific chunking model implementation.
    """
    
    TYPE: Final[str] = "ChunkingModel"
    REQUIRED_EXTRA_KWARGS: Final[List[str]] = ["documents", "db", "pipeline_id"]

    id: int
    pipeline_id: int
    class_name: str
    parameters: Dict[str, Any]
    def __init__(self, **kwargs):
        """
        Initialize the chunking model with any necessary parameters.
        """
        self.db: Session = kwargs.pop("db")
        self.pipeline_id: int = kwargs.pop("pipeline_id")
        self.documents: Dict[int, BaseDocument] = kwargs.pop("documents")
        self.class_name = self.__class__.__name__
        self.parameters = self.validate_and_transform(kwargs)
        self.init_model_in_db()
        self.chunks = self.chunk_documents()
        self.update_chunks_in_db()
        
    @abstractmethod
    def chunk_text(self, text: str, **kwargs) -> List[str]:
        """
        Chunk the input text into smaller pieces.
        
        Args:
            text (str): The input text to be chunked.
            **kwargs: Additional parameters for chunking.

        Returns:
            List[str]: A list of text chunks.
        """
        raise NotImplementedError("Subclasses must implement the chunk_text method.")

    def chunk_document(self, document: BaseDocument) -> Dict[int, Chunk]:
        """
        Chunk a single document using the chunk_text method.

        Args:
            document (BaseDocument): The input document to be chunked.
            **kwargs: Additional parameters for chunking, passed to `chunk_text`.

        Returns:
            Dict[int, Chunk]: A dictionary mapping chunk indices to Chunk objects.
        """
        assert isinstance(document, BaseDocument), "Input must be an instance of BaseDocument."
        text = document.get_text()
        chunks_text = self.chunk_text(text)
        chunks = {}
        for idx, chunk_text in enumerate(chunks_text):
            chunk = Chunk(
                id=None,
                document_position=idx,
                document_id=document.id,
                text=chunk_text,
            )
            chunks[idx] = chunk
        return chunks
    
    def chunk_documents(self) -> Dict[int, Dict[int, Chunk]]:
        """
        Chunk documents using the chunk_document method.

        Returns:
            Dict[int, Dict[int, Chunk]]: A dictionary mapping document IDs to their respective
            dictionaries of chunk indices and Chunk objects.
        """
        chunked_documents = {}
        for document_id, document in self.documents.items():
            chunks = self.chunk_document(document)
            chunked_documents[document_id] = chunks
        return chunked_documents

    def fetch_model_from_db(self):
        """
        Retrieve the chunking model from the database if it exists.
        """
        existing_pipeline: PipelineDBModel = self.db.query(
            PipelineDBModel).filter_by(id=self.pipeline_id).first()
        if existing_pipeline:
            chunking_model_id = existing_pipeline.chunking_model_id
            chunking_model = self.db.query(DBChunkingModel).filter_by(
                id=chunking_model_id).first()
        else:
            chunking_model = self.db.query(DBChunkingModel).filter_by(
                class_name=self.class_name,
                parameters=self.parameters
            ).first()
        if chunking_model:
            self.id = chunking_model.id
            return chunking_model
        self.id = None
        return None

    def create_model_in_db(self) -> DBChunkingModel:
        """
        Store the chunking model in the database.
        """
        new_model = DBChunkingModel(
            class_name=self.class_name,
            parameters=self.parameters,
        )
        self.db.add(new_model)
        self.db.commit()
        self.db.refresh(new_model)
        self.id = new_model.id
        return new_model

    def update_model_in_db(self) -> DBChunkingModel:
        """
        Update the chunking model in the database.
        """
        model = self.db.query(DBChunkingModel).filter_by(id=self.id).first()
        if model:
            # The relationship is managed through the foreign key on RAGPipeline
            # No need to manually manage the pipelines collection here
            self.db.commit()
            self.db.refresh(model)
        return model
    
    def init_model_in_db(self):
        if self.fetch_model_from_db():
            db_model = self.update_model_in_db()
        else:
            db_model = self.create_model_in_db()
        return db_model
    
    def fetch_chunks_from_db(self) -> Dict[int, Dict[int, Chunk]]:
        """
        Fetch all chunks associated with the chunking model from the database.

        Returns:
            Dict[int, Dict[int, Chunk]]: A dictionary mapping document IDs to their respective
            dictionaries of chunk indices and Chunk objects.
        """
        chunks = {}
        for document_id, _ in self.documents.items():
            chunks[document_id] = {}
            stored_chunks = self.db.query(DBChunkModel).filter_by(
                chunking_model_id=self.id,
                document_id=document_id
            )
            for chunk in stored_chunks:
                chunks[document_id][chunk.chunk_index] = Chunk(
                    document_position=chunk.chunk_index,
                    document_id=chunk.document_id,
                    text=chunk.text,
                )
        return chunks
    
    def create_chunks_in_db(self, document_chunks: Dict[int, Chunk]) -> None:
        """
        Store the chunks of a document in the database.

        Args:
            document_chunks (Dict[int, Chunk]): A dictionary mapping chunk indices to Chunk objects.
        """
        for idx, chunk in document_chunks.items():
            db_chunk = DBChunkModel(
                document_id=chunk.document_id,
                chunk_index=chunk.document_position,
                chunking_model_id=self.id,
                text=chunk.text,
                hash=hash_function(chunk.text)
            )
            self.db.add(db_chunk)
            self.db.commit()
            self.chunks[chunk.document_id][idx].id = db_chunk.id


    def update_chunks_in_db(self) -> None:
        """
        Update the chunks in the database if they do not already exist.
        """
        existing_chunks = self.fetch_chunks_from_db()
        for document_id, chunks in self.chunks.items():
            if document_id not in existing_chunks:
                self.create_chunks_in_db(chunks)
                
    def get_chunks(self) -> Dict[int, Dict[int, Chunk]]:
        """
        Get the chunks generated by the chunking model.

        Returns:
            Dict[int, Dict[int, Chunk]]: A dictionary mapping document IDs to their respective
            dictionaries of chunk indices and Chunk objects.
        """
        return self.chunks