import hashlib
import json
import logging
from typing import Any

from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    Chunk as ChunkDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGChunkingModel as ChunkingModelDBModel,
)
from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGChunkSetDocument,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.chunking_models.chunking_model_factory import (
    ChunkingFactoryResult,
)
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.models.RAG.RAG_models_factory import RAGModelsFactory

log = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking lifecycle: chunk set identity, model persistence."""

    def __init__(self, db: Session, registry: ComponentRegistry):
        self._db = db
        self._registry = registry

    # ── Chunk set identity ──

    def _build_chunk_set_signature(
        self, document_ids: list[int], pipeline_config: dict[str, Any]
    ) -> str:
        """Build SHA-256 signature for deterministic chunk set identity."""
        payload = json.dumps(
            {
                "doc_ids": sorted(document_ids),
                "config": dict(sorted(pipeline_config.items())),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get_or_create_chunk_set(
        self,
        document_ids: list[int],
        pipeline_config: dict[str, Any],
    ) -> RAGChunkSet:
        """Deterministic chunk-set identity via SHA-256.

        1. Build signature
        2. Query RAGChunkSet by signature -> return if exists (CACHE HIT)
        3. Create RAGChunkSet + RAGChunkSetDocument rows
        4. Return new chunk set

        Raises RuntimeError on DB error.
        """
        signature = self._build_chunk_set_signature(document_ids, pipeline_config)
        try:
            existing = (
                self._db.query(RAGChunkSet).filter_by(signature=signature).first()
            )
            if existing:
                return existing

            chunk_set = RAGChunkSet(signature=signature, parameters=pipeline_config)
            self._db.add(chunk_set)
            self._db.commit()
            self._db.refresh(chunk_set)

            for doc_id in sorted(document_ids):
                self._db.add(
                    RAGChunkSetDocument(
                        chunk_set_id=chunk_set.id,
                        document_id=doc_id,
                    )
                )
            self._db.commit()
            return chunk_set
        except exc.SQLAlchemyError as e:
            self._db.rollback()
            log.exception(e)
            raise RuntimeError("Database error during chunk set creation.") from e

    # ── Chunking model lifecycle ──

    def create(
        self,
        documents: dict[int, BaseDocument],
        chunk_set_id: int,
        component_name: str,
        params: dict[str, Any],
    ) -> tuple[int, ChunkingFactoryResult]:
        """Lookup-or-create a chunking model and its chunks.

        1. Sort params
        2. Query RAGChunkingModel -> if found, load chunks from DB, return
        3. If not: instantiate via pure factory, persist model + chunks, return

        Returns (db_record_id, ChunkingFactoryResult(model, chunks)).
        """
        sorted_params = dict(sorted(params.items()))

        try:
            existing = (
                self._db.query(ChunkingModelDBModel)
                .filter_by(class_name=component_name, parameters=sorted_params)
                .first()
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise RuntimeError("Database error during chunking model lookup.") from e

        if existing is not None:
            chunks = self._fetch_chunks_from_db(chunk_set_id)
            model_params = {**params, "documents": documents}
            model_class = self._registry[component_name]["class"]
            model = model_class(**model_params)
            model.chunks = chunks
            return existing.id, ChunkingFactoryResult(model=model, chunks=chunks)

        factory = RAGModelsFactory(self._registry)
        result = factory.create_chunking_model(component_name, params, documents)

        try:
            record_id = self._save_db_record(result.model)
            self._persist_chunks(result.chunks, chunk_set_id)
            self._update_chunk_ids(result.model, chunk_set_id)
            return record_id, result
        except exc.SQLAlchemyError as e:
            self._db.rollback()
            log.exception(e)
            raise RuntimeError(
                "Database error during chunking model persistence."
            ) from e

    # ── Private DB helpers ──

    def _save_db_record(self, model) -> int:
        """Persist a chunking model record to the database.

        Args:
            model: Chunking model instance with a ``parameters`` attribute.

        Returns:
            Primary key of the newly created DB record.
        """
        sorted_params = dict(sorted(model.parameters.items()))
        record = ChunkingModelDBModel(
            class_name=model.__class__.__name__,
            parameters=sorted_params,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record.id

    def _fetch_chunks_from_db(self, chunk_set_id: int) -> dict[int, dict[int, Chunk]]:
        """Load all chunks for a chunk set from the database.

        Args:
            chunk_set_id: Chunk set identifier.

        Returns:
            Nested dict keyed by ``document_id`` then ``chunk_index``.
        """
        chunks: dict[int, dict[int, Chunk]] = {}
        db_chunks = (
            self._db.query(ChunkDBModel).filter_by(chunk_set_id=chunk_set_id).all()
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

    def _persist_chunks(
        self, chunks: dict[int, dict[int, Chunk]], chunk_set_id: int
    ) -> None:
        """Write chunk rows to the database.

        Args:
            chunks: Nested dict of chunks keyed by document_id and index.
            chunk_set_id: FK to the owning chunk set.
        """
        for document_id, document_chunks in chunks.items():
            for idx, chunk in document_chunks.items():
                self._db.add(
                    ChunkDBModel(
                        document_id=document_id,
                        chunk_index=idx,
                        chunk_set_id=chunk_set_id,
                        text=chunk.text,
                    )
                )
        self._db.commit()

    def _update_chunk_ids(self, model, chunk_set_id: int) -> None:
        """Patch in-memory chunk ids with their DB-assigned primary keys.

        Args:
            model: Chunking model whose ``chunks`` dict will be mutated.
            chunk_set_id: Chunk set identifier for the DB lookup.
        """
        for document_id, document_chunks in model.get_chunks().items():
            for idx, _chunk in document_chunks.items():
                db_chunk = (
                    self._db.query(ChunkDBModel)
                    .filter_by(
                        document_id=document_id,
                        chunk_index=idx,
                        chunk_set_id=chunk_set_id,
                    )
                    .first()
                )
                if db_chunk is not None:
                    model.chunks[document_id][idx].id = db_chunk.id
