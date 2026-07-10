"""RAG pipeline orchestration.

RAGPipeline receives its dependencies injected (config, factories,
repository, loader) rather than constructing them from raw kwargs.
Orchestrates: document loading → chunk-set creation → chunking →
retrieval → prompt formatting → LLM generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

log = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
)
from DashAI.back.dependencies.database.models import (
    RAGPipeline as PipelineDBModel,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.RAG.chunk_set_utils import get_or_create_chunk_set
from DashAI.back.models.RAG.chunking_models.chunking_model_factory import (
    ChunkingFactoryResult,
)
from DashAI.back.models.RAG.document_loader import DocumentLoader
from DashAI.back.models.RAG.documents import BaseDocument, Chunk
from DashAI.back.models.RAG.llm_factory import LLMFactoryResult
from DashAI.back.models.RAG.pipeline_repository import PipelineRepository
from DashAI.back.models.RAG.prompts.prompt_factory import PromptFactoryResult
from DashAI.back.models.RAG.rag_models_factory import RAGModelsFactory
from DashAI.back.models.RAG.retrievers.retriever_factory import (
    RetrieverFactoryResult,
)
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

if TYPE_CHECKING:
    from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
        BaseChunkingModel,
    )
    from DashAI.back.models.RAG.prompts import Prompt
    from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel


class RAGPipelineError(Exception):
    """Base exception for RAG pipeline errors."""


class RAGPipelineParametersError(RAGPipelineError):
    """Backward-compatible alias for RAGPipelineConfigError."""


class RAGPipelineConfigError(RAGPipelineError):
    """Invalid or missing parameters in pipeline configuration."""


class RAGPipelineInitializationError(RAGPipelineError):
    """Error during RAG pipeline initialization."""


class RAGPipelineRuntimeError(RAGPipelineError):
    """Error during RAG pipeline execution."""


class RAGDatabaseError(RAGPipelineError):
    """Database-related error in RAG pipeline."""


@dataclass(frozen=True)
class ModelRef:
    """Parsed reference to a component model.

    Represents a ``{component: str, params: dict}`` entry from the
    pipeline parameter payload.
    """

    component: str
    params: Dict[str, Any]


@dataclass(frozen=True)
class ChunkReference:
    """A single chunk with its document metadata."""

    document_id: int
    document_name: str
    document_position: int
    text: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_position": self.document_position,
            "text": self.text,
        }


@dataclass(frozen=True)
class RAGGenerationOutput:
    """Typed output from RAGPipeline.generate()."""

    message: Any
    chunks: Dict[str, "ChunkReference"]


@dataclass(frozen=True)
class RAGPipelineConfig:
    """Structured, validated representation of pipeline initialisation kwargs.

    Parses the raw kwargs dict once and provides typed field access,
    eliminating magic strings in the pipeline's __init__.
    """

    session_id: int
    db: Session
    component_registry: ComponentRegistry
    env_rag_path: str
    documents: List[int]
    prompt: ModelRef
    chunking_model: ModelRef
    retriever_model: ModelRef
    generation_model: ModelRef

    _MODEL_KEYS: Tuple[str, str, str, str] = (
        "prompt",
        "chunking_model",
        "retriever_model",
        "generation_model",
    )
    _INFRA_KEYS: Tuple[str, str, str, str] = (
        "session_id",
        "db",
        "component_registry",
        "env_rag_path",
    )
    _PARAM_KEYS: Tuple[str] = ("documents",)

    @classmethod
    def validate_model_refs(cls, params: Dict[str, Any]) -> None:
        for key in cls._MODEL_KEYS:
            if key not in params:
                raise RAGPipelineConfigError(f"Missing '{key}'")
            raw = params[key]
            if not isinstance(raw, dict):
                raise RAGPipelineConfigError(
                    f"'{key}' must be a dict, got {type(raw).__name__}"
                )
            if "component" not in raw:
                raise RAGPipelineConfigError(f"Missing 'component' in '{key}'")
            if "params" not in raw:
                raise RAGPipelineConfigError(f"Missing 'params' in '{key}'")
        if "documents" not in params:
            raise RAGPipelineConfigError("Missing required parameter 'documents'")

    @classmethod
    def from_kwargs(cls, **kwargs: Any) -> "RAGPipelineConfig":
        missing: List[str] = []
        for key in cls._INFRA_KEYS:
            if key not in kwargs:
                missing.append(key)
        for key in cls._PARAM_KEYS:
            if key not in kwargs:
                missing.append(key)
        for key in cls._MODEL_KEYS:
            if key not in kwargs:
                missing.append(key)
        if missing:
            raise RAGPipelineConfigError(
                f"Missing required parameters: {sorted(missing)}"
            )

        model_refs: Dict[str, ModelRef] = {}
        for key in cls._MODEL_KEYS:
            raw = kwargs[key]
            if not isinstance(raw, dict):
                raise RAGPipelineConfigError(
                    f"'{key}' must be a dict, got {type(raw).__name__}"
                )
            if "component" not in raw:
                raise RAGPipelineConfigError(f"Missing 'component' in '{key}'")
            if "params" not in raw:
                raise RAGPipelineConfigError(f"Missing 'params' in '{key}'")
            model_refs[key] = ModelRef(
                component=raw["component"],
                params=raw["params"],
            )

        all_known: set[str] = (
            set(cls._INFRA_KEYS) | set(cls._PARAM_KEYS) | set(cls._MODEL_KEYS)
        )
        extra: set[str] = set(kwargs) - all_known
        if extra:
            log.warning(
                "Unknown parameters passed to RAGPipelineConfig.from_kwargs(): %s. "
                "These keys are not recognized and will cause the pipeline to fail. "
                "Check if session parameters contain extra metadata keys.",
                sorted(extra),
            )
            raise RAGPipelineConfigError(
                f"Unknown parameters: {sorted(extra)}. "
                "These keys are not recognized pipeline configuration parameters."
            )

        return cls(
            session_id=kwargs["session_id"],
            db=kwargs["db"],
            component_registry=kwargs["component_registry"],
            env_rag_path=kwargs["env_rag_path"],
            documents=kwargs["documents"],
            prompt=model_refs["prompt"],
            chunking_model=model_refs["chunking_model"],
            retriever_model=model_refs["retriever_model"],
            generation_model=model_refs["generation_model"],
        )


class RAGPipelineSchema(BaseSchema):
    documents: schema_field(
        list_field(int_field(gt=0)),
        placeholder=None,
        description=MultilingualString(
            en="List of document IDs to use in the RAG pipeline.",
            es="Lista de IDs de documentos a usar en el pipeline RAG.",
        ),
    )  # type: ignore

    prompt: schema_field(
        component_field(parent="Prompt"),
        placeholder={"component": "DefaultRAGGenerationPrompt", "params": {}},
        description=MultilingualString(
            en="Prompt template used in the RAG pipeline.",
            es="Plantilla de prompt usada en el pipeline RAG.",
        ),
    )  # type: ignore

    chunking_model: schema_field(
        component_field(parent="BaseChunkingModel"),
        description=MultilingualString(
            en="Chunking model used to split documents into smaller pieces.",
            es="Modelo de fragmentación para dividir documentos en piezas.",
        ),
        placeholder={"component": "CharacterChunkModel", "params": {}},
    )  # type: ignore

    retriever_model: schema_field(
        component_field(parent="RetrieverModel"),
        placeholder={"component": "TFIDFRetriever", "params": {}},
        description=MultilingualString(
            en="Retriever component used in the RAG pipeline.",
            es="Componente recuperador usado en el pipeline RAG.",
        ),
    )  # type: ignore

    generation_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder={"component": "", "params": {}},
        description=MultilingualString(
            en="Text generation model used in the RAG pipeline.",
            es="Modelo de generación de texto usado en el pipeline RAG.",
        ),
    )  # type: ignore


class RAGPipeline(BaseGenerativeModel):
    """Retrieval-Augmented Generation pipeline.

    Receives dependencies injected — does not construct factories,
    repositories, or loaders. The caller (RAGJob) builds them from
    the current DB session and passes them in.

    Orchestrates: document loading → chunk-set creation → chunking →
    retrieval → prompt formatting → LLM generation.
    """

    COMPATIBLE_COMPONENTS: List[str] = ["RAGTask"]
    SCHEMA: type[BaseSchema] = RAGPipelineSchema

    session_id: int
    pipeline_id: int
    documents_ids: List[int]
    documents: Dict[int, BaseDocument]
    prompt_model: Prompt
    chunking_model_id: int
    chunking_model: BaseChunkingModel
    chunks: Dict[int, Dict[int, Chunk]]
    retriever: RetrieverModel
    llm_model: TextToTextGenerationTaskModel

    DISPLAY_NAME: str = MultilingualString(
        en="RAG Pipeline",
        es="Flujo de RAG",
        pt="Pipeline RAG",
    )
    DESCRIPTION: str = MultilingualString(
        en="Pipeline for Retrieval-Augmented Generation (RAG) tasks, orchestrating document loading, chunking, retrieval, prompt formatting, and LLM generation.",
        es="Pipeline para tareas de Generación Aumentada por Recuperación (RAG), orquestando la carga de documentos, chunking, recuperación, formateo de prompts y generación con LLM.",
        pt="Pipeline para tarefas de Geração Aumentada por Recuperação (RAG), orquestrando carregamento de documentos, chunking, recuperação, formatação de prompts e geração com LLM.",
    )
    COLOR: str = "#e12885"
    ICON: str = "Grading"
    MODEL_NAME: str = "RAGPipeline"

    def __init__(
        self,
        config: RAGPipelineConfig,
        models: RAGModelsFactory,
        repo: PipelineRepository,
        doc_loader: DocumentLoader,
    ) -> None:
        pipeline_record: PipelineDBModel = repo.ensure_db_record(
            config.session_id,
        )

        documents = doc_loader.load(config.documents)

        chunk_set: RAGChunkSet = get_or_create_chunk_set(
            db=config.db,
            document_ids=config.documents,
            pipeline_config={
                "chunking_model": {
                    "component": config.chunking_model.component,
                    "params": config.chunking_model.params,
                }
            },
        )

        prompt_result: PromptFactoryResult = models.create_prompt(
            config.prompt.component,
            config.prompt.params,
        )

        chunking_result: ChunkingFactoryResult = models.create_chunking_model(
            documents,
            chunk_set.id,
            config.chunking_model.component,
            config.chunking_model.params,
        )

        retriever_result: RetrieverFactoryResult = models.create_retriever(
            pipeline_record.id,
            chunking_result.chunks,
            chunk_set.id,
            config.retriever_model.component,
            config.retriever_model.params,
        )

        llm_result: LLMFactoryResult = models.create_llm(
            config.generation_model.component,
            config.generation_model.params,
        )

        repo.update_db_record(
            session_id=config.session_id,
            chunking_model_id=chunking_result.db_record_id,
            prompt_id=prompt_result.db_record_id,
            generation_model_id=llm_result.db_record_id,
        )

        self.session_id = config.session_id
        self.pipeline_id = pipeline_record.id
        self.documents_ids = config.documents
        self.documents = documents
        self.prompt_model = prompt_result.model
        self.chunking_model_id = chunking_result.db_record_id
        self.chunking_model = chunking_result.model
        self.chunks = chunking_result.chunks
        self.retriever = retriever_result.model
        self.llm_model = llm_result.model

    def single_interaction(
        self,
        query: str,
    ) -> List[Chunk]:
        """Retrieve the top-K chunks for a single query.

        Parameters
        ----------
        query : str
            The search query string.

        Returns
        -------
        List[Chunk]
            Ranked list of retrieved chunks.

        Raises
        ------
        RAGPipelineRuntimeError
            If the retriever fails.
        """
        try:
            return self.retriever.retrieve(query)
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Document retrieval failed: {str(e)}") from e

    def _build_chunk_references(
        self,
        chunks: List[Chunk],
    ) -> Tuple[str, Dict[str, ChunkReference]]:
        """Build a text block and reference map from retrieved chunks.

        Parameters
        ----------
        chunks : List[Chunk]
            Chunks returned by the retriever.

        Returns
        -------
        Tuple[str, Dict[str, ChunkReference]]
            Joined chunk texts and a mapping from chunk key to ChunkReference.
        """
        chunks_texts: List[str] = []
        chunk_dict: Dict[str, ChunkReference] = {}
        for retrieved_chunk in chunks:
            document_id: int = retrieved_chunk.document_id
            document: BaseDocument = self.documents[document_id]
            chunk_position: int = retrieved_chunk.document_position
            chunk_text: str = retrieved_chunk.text
            chunk_ref: str = f"{document_id}_{chunk_position}"
            chunk_dict[chunk_ref] = ChunkReference(
                document_id=document_id,
                document_name=document.file_name,
                document_position=chunk_position,
                text=chunk_text,
            )
            chunks_texts.append(
                f"Document {document.file_name}, "
                f"chunk nº {chunk_position}, text:\n {chunk_text}"
            )
        return "\n\n".join(chunks_texts), chunk_dict

    def generate(
        self,
        input_data: Tuple[Dict[str, str], ...],
    ) -> RAGGenerationOutput:
        """Run the full RAG pipeline: retrieve → format → generate.

        Parameters
        ----------
        input_data : Tuple[Dict[str, str], ...]
            Chat-format input with history as earlier entries and the
            current user message as the last entry.

        Returns
        -------
        RAGGenerationOutput
            The generated message and the chunks used for retrieval.

        Raises
        ------
        RAGPipelineRuntimeError
            If any stage fails (retrieval, formatting, or generation).
        """
        if not input_data:
            raise RAGPipelineRuntimeError("input_data must not be empty.")
        try:
            input_dict: Dict[str, str] = input_data[-1]
            input_message: str = input_dict["content"]
            history: Tuple[Dict[str, str], ...] = input_data[:-1]
            chunks: List[Chunk] = self.single_interaction(input_message)
        except Exception as e:
            raise RAGPipelineRuntimeError(f"Failed during retrieval: {str(e)}") from e
        try:
            chunks_text: str
            chunk_dict: Dict[str, ChunkReference]
            chunks_text, chunk_dict = self._build_chunk_references(chunks)
            prompt: str = self.prompt_model.format(
                input=input_message,
                chunks=chunks_text,
            )
        except Exception as e:
            raise RAGPipelineRuntimeError(
                f"Failed during prompt formatting: {str(e)}"
            ) from e
        try:
            model_input: List[Dict[str, str]] = list(history) + [
                {"role": "user", "content": prompt}
            ]
            # NOTE: Output is not streamed — the user waits for the full response.
            output: List[Any] = self.llm_model.generate(model_input)
            return RAGGenerationOutput(message=output[0], chunks=chunk_dict)
        except Exception as e:
            raise RAGPipelineRuntimeError(
                f"Failed during LLM generation: {str(e)}"
            ) from e
