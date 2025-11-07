from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from DashAI.back.dependencies.database.models import Chunk
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.extra_args_enum import (
    PIPELINE_ID,
    DB,
    COMPONENT_REGISTRY,
    ENV_RAG_PATH,
    DOCUMENTS,
    CHUNKS,
    CHUNKING_MODEL_ID
)

class ModelsFactory(ABC):
    
    def __init__(
            self,
            pipeline_id: int, 
            db: Session, 
            component_registry: ComponentRegistry,
            env_rag_path: str, 
            documents: Dict[int, BaseDocument],
            chunks: Dict[int, Dict[int, Chunk]],
            chunking_model_id: int
            ):
        self.db = db
        self.extra_kwargs = {
            PIPELINE_ID: pipeline_id,
            DB: db,
            COMPONENT_REGISTRY: component_registry,
            ENV_RAG_PATH: env_rag_path,
            DOCUMENTS: documents,
            CHUNKS: chunks,
            CHUNKING_MODEL_ID: chunking_model_id
        }
        self.pipeline_id = pipeline_id
        self.env_rag_path = env_rag_path
        self.documents = documents
        self.chunks = chunks
        self.chunking_model_id = chunking_model_id

    @abstractmethod
    def load_model_from_db(self, model_class: RetrieverModel|BaseChunkingModel, model_params: Dict[str, Any], **kwargs) -> RetrieverModel|BaseChunkingModel:
        raise NotImplementedError

    @abstractmethod
    def save_model_to_db(self, instance: RetrieverModel|BaseChunkingModel, **kwargs) -> int:
        raise NotImplementedError
    
    @abstractmethod
    def update_db_models(self, instance: RetrieverModel|BaseChunkingModel, **kwargs) -> None:
        raise NotImplementedError

    def init_component(self, model_class: RetrieverModel|BaseChunkingModel, model_params: Dict[str, Any], **kwargs) -> RetrieverModel|BaseChunkingModel:
        loaded_model = self.load_model_from_db(model_class, model_params, **kwargs)
        if loaded_model is not None:
            return [loaded_model.id, loaded_model]
        for kwarg in model_class.REQUIRED_EXTRA_KWARGS:
            model_params[kwarg] = self.extra_kwargs[kwarg]
        created_model = model_class(**model_params)
        id = self.save_model_to_db(created_model, **kwargs)
        created_model.set_id(id)
        return [id, created_model]