from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.models.RAG.models_factory import ModelsFactory
from DashAI.back.dependencies.database.models import (
    RAGChunkingModel as ChunkingModelDBModel,
    Chunk as ChunkDBModel
)
from sqlalchemy.orm import Session
from typing import Any, Dict, List
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.utils import hash_function


class ChunkingModelsFactory(ModelsFactory):
    """
    Class responsible for creating chunking model instances and storing their models in database.
    """

    def __init__(
            self,
            db: Session, 
            documents: Dict[int, BaseDocument]
            ):
        super().__init__(
            db = db,
            pipeline_id = None,
            component_registry = None,
            env_rag_path = None,
            documents = documents,
            chunks = None,
            chunking_model_id = None
        )

    def load_model_from_db(self, model_class: BaseChunkingModel, model_params: Dict[str, Any], **kwargs) -> BaseChunkingModel|None:
        assert issubclass(model_class, BaseChunkingModel), "model_class must be a subclass of BaseChunkingModel"
        # Sort parameters to ensure consistent hashing
        model_params = dict(sorted(model_params.items()))
        class_name = model_class.__name__
        existing_model = self.db.query(ChunkingModelDBModel).filter_by(
            class_name=class_name,
            parameters=model_params
        ).first()
        if existing_model:
            model_params['documents'] = self.documents
            instance = model_class(**model_params)
            instance.set_id(existing_model.id)
            return instance
    
    def save_model_to_db(self, instance: BaseChunkingModel, **kwargs) -> int:
        assert isinstance(instance, BaseChunkingModel), "instance must be an instance of BaseChunkingModel"
        parameters = dict(sorted(instance.parameters.items()))
        db_model = ChunkingModelDBModel(
            class_name=instance.class_name,
            parameters=parameters,
        )
        self.db.add(db_model)
        self.db.commit()
        self.db.refresh(db_model)
        return db_model.id

    def fetch_chunks_from_db(self, chunking_model_id: int) -> Dict[int, Dict[int, Chunk]]:
        chunks = {}
        db_chunks = self.db.query(ChunkDBModel).filter_by(
            chunking_model_id=chunking_model_id
        ).all()
        for db_chunk in db_chunks:
            if db_chunk.document_id not in chunks:
                chunks[db_chunk.document_id] = {}
            chunk = Chunk(
                id=db_chunk.id,
                document_id=db_chunk.document_id,
                document_position=db_chunk.chunk_index,
                text=db_chunk.text
            )
            chunks[db_chunk.document_id][db_chunk.chunk_index] = chunk
        return chunks

    def create_chunks_in_db(self, chunks: Dict[int, Dict[int, Chunk]], chunking_model_id: int):
        """
        Store the chunks of a document in the database.

        Args:
            document_chunks (Dict[int, Chunk]): A dictionary mapping chunk indices to Chunk objects.
        """
        for document_id, document_chunks in chunks.items():
            for idx, chunk in document_chunks.items():
                db_chunk = ChunkDBModel(
                    document_id=document_id,
                    chunk_index=idx,
                    chunking_model_id=chunking_model_id,
                    text=chunk.text,
                )
                self.db.add(db_chunk)
        self.db.commit()
        self.db.flush()


    def update_db_models(self, instance: BaseChunkingModel, **kwargs):
        """
        Update the chunks in the database if they do not already exist.
        """
        existing_chunks = self.fetch_chunks_from_db(instance.get_id())
        chunks_to_create = {}
        for document_id, document_chunks in instance.get_chunks().items():
            if document_id not in existing_chunks:
                chunks_to_create[document_id] = document_chunks
            else:
                for idx, chunk in document_chunks.items():
                    if idx not in existing_chunks[document_id]:
                        chunks_to_create[document_id][idx] = chunk
        self.create_chunks_in_db(chunks_to_create, instance.get_id())

        # update the chunks ids in the instance's chunks
        for document_id, document_chunks in instance.get_chunks().items():
            for idx, chunk in document_chunks.items():
                db_chunk = self.db.query(ChunkDBModel).filter_by(
                    document_id=document_id,
                    chunk_index=idx,
                    chunking_model_id=instance.get_id()
                ).first()
                instance.chunks[document_id][idx].id = db_chunk.id
                assert instance.chunks[document_id][idx].id is not None, "Chunk ID should not be None after fetching from DB."