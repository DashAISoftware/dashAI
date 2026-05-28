"""Abstract Factory (GoF) for RAG component creation.

RAGModelsFactory provides a unified interface for creating the four
RAG component types: prompts, chunking models, retrievers, and LLMs.

Each ``create_*`` method delegates to a specialised sub-factory that
encapsulates the component's full lifecycle (DB-record resolution,
instantiation, and persistence).
"""

from typing import Any, Dict

from sqlalchemy.orm import Session

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.chunking_models.chunking_model_factory import (
    ChunkingFactoryResult,
    ChunkingModelFactory,
)
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.models.RAG.llm_factory import (
    LLMFactory,
    LLMFactoryResult,
)
from DashAI.back.models.RAG.prompts.prompt_factory import (
    PromptFactory,
    PromptFactoryResult,
)
from DashAI.back.models.RAG.retrievers.retriever_factory import (
    RetrieverFactory,
    RetrieverFactoryResult,
)


class RAGModelsFactory:
    """Abstract Factory for the family of RAG components.

    Provides four ``create_*`` methods, each delegating to a
    specialised sub-factory. Shared dependencies (db, registry,
    env_rag_path) are injected once via the constructor.
    """

    def __init__(
        self,
        db: Session,
        registry: ComponentRegistry,
        env_rag_path: str,
    ):
        self._db = db
        self._registry = registry
        self._env_rag_path = env_rag_path

    def create_prompt(
        self,
        component_name: str,
        params: Dict[str, Any],
    ) -> PromptFactoryResult:
        """Create a prompt with lookup-or-create semantics."""
        factory = PromptFactory(self._db, self._registry)
        return factory.create(component_name, params)

    def create_chunking_model(
        self,
        documents: Dict[int, BaseDocument],
        chunk_set_id: int,
        component_name: str,
        params: Dict[str, Any],
    ) -> ChunkingFactoryResult:
        """Create a chunking model, chunk documents, and persist chunks."""
        factory = ChunkingModelFactory(
            self._db,
            self._registry,
            documents,
            chunk_set_id,
        )
        return factory.create(component_name, params)

    def create_retriever(
        self,
        pipeline_id: int,
        chunks: Dict[int, Dict[int, Chunk]],
        chunk_set_id: int,
        component_name: str,
        params: Dict[str, Any],
    ) -> RetrieverFactoryResult:
        """Create a retriever with full persistence lifecycle."""
        factory = RetrieverFactory(
            self._db,
            pipeline_id,
            self._registry,
            self._env_rag_path,
            chunks,
            chunk_set_id,
        )
        return factory.create(component_name, params)

    def create_llm(
        self,
        component_name: str,
        params: Dict[str, Any],
    ) -> LLMFactoryResult:
        """Create an LLM with lookup-or-create DB semantics."""
        factory = LLMFactory(self._db, self._registry)
        return factory.create(component_name, params)
