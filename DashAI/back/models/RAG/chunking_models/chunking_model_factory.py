"""Factory for chunking models with full lifecycle encapsulation.

Single-call interface: create() handles DB-record resolution,
model instantiation, document chunking, and chunk persistence.
"""

from dataclasses import dataclass
from typing import Any, Dict

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    Chunk as ChunkDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGChunkingModel as ChunkingModelDBModel,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk


@dataclass(frozen=True)
class ChunkingFactoryResult:
    """Result of chunking model creation via ChunkingModelFactory."""

    db_record_id: int
    model: BaseChunkingModel
    chunks: Dict[int, Dict[int, Chunk]]


class ChunkingModelFactory:
    """Creates a chunking model, chunks documents, and persists everything.

    Encapsulates the full lifecycle: DB-record resolution, model
    instantiation, document splitting, and chunk persistence.
    The caller calls ``create()`` once — no post-call required.
    """

    def __init__(
        self,
        db: Session,
        registry: ComponentRegistry,
        documents: Dict[int, BaseDocument],
        chunk_set_id: int,
    ):
        self._db = db
        self._registry = registry
        self._documents = documents
        self._chunk_set_id = chunk_set_id

    def create(
        self,
        component_name: str,
        params: Dict[str, Any],
    ) -> ChunkingFactoryResult:
        """Full lifecycle: resolve DB record → instantiate → chunk → persist.

        Returns:
            ChunkingFactoryResult with record_id, model, and populated chunks.
        """
        sorted_params: Dict[str, Any] = dict(sorted(params.items()))

        existing_record = self._resolve_db_record(component_name, sorted_params)
        if existing_record is not None:
            params["documents"] = self._documents
            model_class = self._registry[component_name]["class"]
            model = model_class(**params)
            model.set_id(existing_record.id)
            self._update_chunk_ids(model)
            return ChunkingFactoryResult(
                db_record_id=existing_record.id,
                model=model,
                chunks=model.get_chunks(),
            )

        model_class = self._registry[component_name]["class"]
        params["documents"] = self._documents
        model = model_class(**params)
        record_id = self._save_db_record(model)

        self._persist_chunks(model)

        return ChunkingFactoryResult(
            db_record_id=record_id,
            model=model,
            chunks=model.get_chunks(),
        )

    def _resolve_db_record(
        self, class_name: str, sorted_params: Dict[str, Any]
    ) -> ChunkingModelDBModel | None:
        return (
            self._db.query(ChunkingModelDBModel)
            .filter_by(class_name=class_name, parameters=sorted_params)
            .first()
        )

    def _save_db_record(self, model: BaseChunkingModel) -> int:
        sorted_params = dict(sorted(model.parameters.items()))
        record = ChunkingModelDBModel(
            class_name=model.__class__.__name__,
            parameters=sorted_params,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        model.set_id(record.id)
        return record.id

    def _fetch_chunks_from_db(self) -> Dict[int, Dict[int, Chunk]]:
        chunks: Dict[int, Dict[int, Chunk]] = {}
        db_chunks = (
            self._db.query(ChunkDBModel)
            .filter_by(chunk_set_id=self._chunk_set_id)
            .all()
        )
        for db_chunk in db_chunks:
            if db_chunk.document_id not in chunks:
                chunks[db_chunk.document_id] = {}
            chunk = Chunk(
                id=db_chunk.id,
                document_id=db_chunk.document_id,
                document_position=db_chunk.chunk_index,
                text=db_chunk.text,
            )
            chunks[db_chunk.document_id][db_chunk.chunk_index] = chunk
        return chunks

    def _create_chunks_in_db(self, chunks: Dict[int, Dict[int, Chunk]]) -> None:
        for document_id, document_chunks in chunks.items():
            for idx, chunk in document_chunks.items():
                self._db.add(
                    ChunkDBModel(
                        document_id=document_id,
                        chunk_index=idx,
                        chunk_set_id=self._chunk_set_id,
                        text=chunk.text,
                    )
                )
        self._db.commit()
        self._db.flush()

    def _update_chunk_ids(self, model: BaseChunkingModel) -> None:
        for document_id, document_chunks in model.get_chunks().items():
            for idx, _chunk in document_chunks.items():
                db_chunk = (
                    self._db.query(ChunkDBModel)
                    .filter_by(
                        document_id=document_id,
                        chunk_index=idx,
                        chunk_set_id=self._chunk_set_id,
                    )
                    .first()
                )
                if db_chunk is not None:
                    model.chunks[document_id][idx].id = db_chunk.id

    def _persist_chunks(self, model: BaseChunkingModel) -> None:
        existing_chunks = self._fetch_chunks_from_db()
        chunks_to_create: Dict[int, Dict[int, Chunk]] = {}
        for document_id, document_chunks in model.get_chunks().items():
            if document_id not in existing_chunks:
                chunks_to_create[document_id] = document_chunks
            else:
                for idx, chunk in document_chunks.items():
                    if idx not in existing_chunks[document_id]:
                        if document_id not in chunks_to_create:
                            chunks_to_create[document_id] = {}
                        chunks_to_create[document_id][idx] = chunk

        self._create_chunks_in_db(chunks_to_create)

        self._update_chunk_ids(model)
