"""Service that orchestrates the complete retriever lifecycle.

Handles lookup-or-create, factory invocation, DB persistence, and embedding
matrix storage for both unit retrievers (dense/sparse) and composite retrievers
(with recursive children).

The lifecycle is divided into three explicit phases:
    Phase 1 — Construction: build the model in memory (no I/O, no DB).
    Phase 2 — Initialization: heavy I/O (embeddings, similarity matrices).
    Phase 3 — Persistence: save to DB (bridge records, sub-table rows).
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from DashAI.back.core.schema_fields.utils import normalize_payload
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverEmptyChildrenError,
    RAGRetrieverError,
    RAGRetrieverMissingParameterError,
)
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import DenseRetriever
from DashAI.back.models.RAG.retrievers.persistence import (
    DensePersistence,
    SparsePersistence,
)
from DashAI.back.models.RAG.retrievers.retriever_factory import (
    RetrieverFactory,
)
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever
from DashAI.back.models.RAG.utils import hash_function
from DashAI.back.services.RAG.embedding_storage_service import EmbeddingStorageService
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrieverSetupResult:
    db_record_id: int
    model: RetrieverModel


class RetrieverSetupService:
    """Orchestrates the complete retriever lifecycle.

    Combines the pure :class:`RetrieverFactory` with database persistence
    and embedding storage so that higher-level pipeline code only needs to
    call a single ``setup()`` method per retriever configuration.

    The lifecycle is divided into three explicit phases:
        1. Construction — build the model in memory (no I/O, no DB).
        2. Initialization — heavy I/O (embeddings, similarity matrices).
        3. Persistence — save to DB (bridge records, sub-table rows).
    """

    def __init__(
        self,
        db: Session,
        registry: ComponentRegistry,
        env_RAG_path: str,  # noqa: N803
        chunks: dict[int, dict[int, Chunk]],
        chunk_set_id: int,
        pipeline_id: int,
    ):
        """Initialize the retriever setup service.

        Args:
            db: SQLAlchemy session.
            registry: Application component registry.
            env_RAG_path: Base RAG data directory path.
            chunks: Nested dict of chunks keyed by document_id and index.
            chunk_set_id: FK to the owning chunk set.
            pipeline_id: FK to the owning pipeline.
        """
        self._db = db
        self._registry = registry
        self._env_RAG_path = env_RAG_path
        self._chunks = chunks
        self._chunk_set_id = chunk_set_id
        self._pipeline_id = pipeline_id
        self._db_service = RetrieverDBService(db)
        self._embedding_service = EmbeddingStorageService(
            env_RAG_path, self._db_service
        )

    # ── Public API ─────────────────────────────────────────────────────

    def build_model(
        self,
        component_name: str,
        params: dict[str, Any],
        persistence: DensePersistence | SparsePersistence | None = None,
    ) -> RetrieverModel:
        """Phase 1: Build model in memory. No I/O, no DB."""
        factory = RetrieverFactory(self._registry, self._env_RAG_path, self._chunks)
        result = factory.create(component_name, params, persistence)
        return result.model

    def initialize_model(self, model: RetrieverModel) -> None:
        """Phase 2: Initialize model (load embeddings, similarity matrices)."""
        model.init_model()

    def persist_model(
        self, model: RetrieverModel, component_name: str, sorted_params: dict
    ) -> int:
        """Phase 3: Persist to DB and return bridge_id."""
        bridge_id = self._save_unit(model, sorted_params)
        model.set_id(bridge_id)
        return bridge_id

    def setup(
        self, component_name: str, params: dict[str, Any]
    ) -> RetrieverSetupResult:
        """Complete retriever setup: build -> initialize -> persist.

        Parameters
        ----------
        component_name : str
            Registered component name (e.g. ``"DenseEmbeddingRetriever"``).
        params : dict[str, Any]
            Raw frontend-style configuration parameters.

        Returns
        -------
        RetrieverSetupResult
            Tuple of the database record id and the fully-initialised model.
        """
        params = normalize_payload(params)
        model_class = self._registry[component_name]["class"]

        if issubclass(model_class, CompositeRetriever):
            return self._setup_composite(model_class, params)

        sorted_params = dict(sorted(params.items()))
        loaded = self._load_unit_from_db(
            model_class, model_class.__name__, sorted_params
        )
        if loaded is not None:
            return RetrieverSetupResult(db_record_id=loaded.get_id(), model=loaded)

        persistence = self._build_persistence_for(model_class, params)
        model = self.build_model(component_name, params, persistence)

        self.initialize_model(model)

        bridge_id = self.persist_model(model, component_name, sorted_params)
        return RetrieverSetupResult(db_record_id=bridge_id, model=model)

    # ── Private: Composite ─────────────────────────────────────────────

    def _setup_composite(
        self, model_class: type, params: dict[str, Any]
    ) -> RetrieverSetupResult:
        """Set up a composite retriever (Sequential/Parallel) with children.

        Checks the DB cache first; if found, returns the cached model.
        Otherwise recursively sets up each child and persists the composite.

        Args:
            model_class: The composite retriever class.
            params: Configuration parameters including ``children``.

        Returns:
            A result with the bridge DB record id and initialized model.

        Raises:
            RAGRetrieverEmptyChildrenError: If ``children`` is empty.
        """
        existing = self._load_composite_from_db(model_class, params)
        if existing is not None:
            result = RetrieverSetupResult(
                db_record_id=existing.get_id(),
                model=existing,
            )
            return result

        children_configs = params.get("children", [])
        if issubclass(model_class, CompositeRetriever) and not children_configs:
            raise RAGRetrieverEmptyChildrenError(
                "Composite retriever must have at least one child"
            )
        children = [self._setup_child(c) for c in children_configs]
        params["children"] = [c.model for c in children]

        model = model_class(**params)
        bridge_id = self._db_service.save_composite(
            model_class.__name__,
            self._pipeline_id,
            [c.db_record_id for c in children],
        ).id
        model.set_id(bridge_id)
        return RetrieverSetupResult(db_record_id=bridge_id, model=model)

    def _setup_child(self, child_config: dict) -> RetrieverSetupResult:
        if "component" not in child_config or "params" not in child_config:
            raise RAGRetrieverMissingParameterError(
                f"Missing 'component' or 'params' in child config: {child_config}"
            )
        return self.setup(
            component_name=child_config["component"],
            params=child_config["params"],
        )

    def _load_composite_from_db(
        self, model_class: type, params: dict[str, Any]
    ) -> RetrieverModel | None:
        """Attempt to load a composite retriever from the database cache.

        Recursively loads children and rebuilds the composite in memory.

        Args:
            model_class: The composite retriever class.
            params: Configuration parameters.

        Returns:
            A fully initialized composite retriever, or ``None`` if not cached.
        """
        bridge = self._db_service.find_composite(
            self._pipeline_id, model_class.__name__
        )
        if bridge is None:
            return None
        child_links = self._db_service.find_composite_children(bridge.id)
        if not child_links:
            return None
        children = []
        for link in child_links:
            child_bridge = self._db_service.get_bridge_by_id(link.child_id)
            if child_bridge is None:
                return None
            child_params = self._load_child_params(
                child_bridge.id, child_bridge.class_name
            )
            if child_params is None:
                return None
            children.append(
                self.setup(
                    component_name=child_bridge.class_name,
                    params=child_params,
                ).model,
            )
        model_class = self._registry[model_class.__name__]["class"]
        model = model_class(
            children=children,
            **{k: v for k, v in params.items() if k != "children"},
        )
        model.set_id(bridge.id)
        return model

    def _load_child_params(
        self, bridge_id: int, class_name: str
    ) -> dict[str, Any] | None:
        """Load a child retriever's persisted parameters from the DB.

        Checks both sparse and dense sub-tables for the given bridge.

        Args:
            bridge_id: Bridge record id of the child.
            class_name: Retriever class name.

        Returns:
            Sorted parameters dict, or ``None`` if no sub-table record found.
        """
        sparse = self._db_service.find_sparse_by_bridge_id(bridge_id)
        if sparse is not None and sparse.parameters is not None:
            return dict(sorted(sparse.parameters.items()))
        dense = self._db_service.find_dense_by_bridge_id(bridge_id)
        if dense is not None and dense.parameters is not None:
            return dict(sorted(dense.parameters.items()))
        return None

    # ── Private: Unit ──────────────────────────────────────────────────

    def _load_unit_from_db(
        self, model_class: type, class_name: str, sorted_params: dict[str, Any]
    ) -> RetrieverModel | None:
        """Load a unit retriever (dense or sparse) from the DB cache.

        Args:
            model_class: Retriever model class.
            class_name: Component class name string.
            sorted_params: Deterministically sorted parameters.

        Returns:
            Initialized retriever model, or ``None`` if not cached.
        """
        if issubclass(model_class, DenseRetriever):
            return self._load_dense(class_name, sorted_params)
        if issubclass(model_class, SparseRetriever):
            return self._load_sparse(class_name, sorted_params)
        return None

    def _load_dense(
        self, class_name: str, sorted_params: dict[str, Any]
    ) -> RetrieverModel | None:
        """Load a dense retriever from the DB cache by its natural key.

        Args:
            class_name: Component class name string.
            sorted_params: Deterministically sorted parameters.

        Returns:
            Fully initialized DenseRetriever, or ``None`` if not cached.

        Raises:
            SQLAlchemyError: On database lookup failure.
        """
        try:
            record = self._db_service.find_dense(
                class_name, sorted_params, self._chunk_set_id
            )
        except SQLAlchemyError:
            log.exception("Database error during dense retriever lookup.")
            raise
        if record is None:
            return None
        persistence = self._build_dense_persistence(record.embedding_model_id)
        factory = RetrieverFactory(self._registry, self._env_RAG_path, self._chunks)
        result = factory.create(
            class_name, dict(sorted_params), persistence=persistence
        )
        model = result.model
        model.init_model()
        bridge = self._db_service.find_bridge_for_sub_table(record, class_name)
        if bridge is not None:
            model.set_id(bridge.id)
        return model

    def _load_sparse(
        self, class_name: str, sorted_params: dict[str, Any]
    ) -> RetrieverModel | None:
        """Load a sparse retriever from the DB cache by its natural key.

        Args:
            class_name: Component class name string.
            sorted_params: Deterministically sorted parameters.

        Returns:
            Fully initialized SparseRetriever, or ``None`` if not cached.

        Raises:
            SQLAlchemyError: On database lookup failure.
        """
        try:
            record = self._db_service.find_sparse(
                class_name, sorted_params, self._chunk_set_id
            )
        except SQLAlchemyError:
            log.exception("Database error during sparse retriever lookup.")
            raise
        if record is None:
            return None
        persistence = SparsePersistence(model_dir=record.storage_folder)
        factory = RetrieverFactory(self._registry, self._env_RAG_path, self._chunks)
        result = factory.create(
            class_name, dict(sorted_params), persistence=persistence
        )
        model = result.model
        model.init_model()
        bridge = self._db_service.find_bridge_for_sub_table(record, class_name)
        if bridge is not None:
            model.set_id(bridge.id)
        return model

    def _build_persistence_for(
        self, model_class: type, params: dict
    ) -> DensePersistence | SparsePersistence:
        """Build the appropriate persistence object for a retriever type.

        Args:
            model_class: Retriever model class.
            params: Configuration parameters.

        Returns:
            A DensePersistence or SparsePersistence instance.

        Raises:
            RAGRetrieverError: If the retriever type is unsupported.
        """
        if issubclass(model_class, DenseRetriever):
            return self._build_dense_persistence_for(params)
        elif issubclass(model_class, SparseRetriever):
            return self._build_sparse_persistence_for(model_class, params)
        else:
            raise RAGRetrieverError(
                f"Unsupported retriever type: {model_class.__name__}"
            )

    def _build_dense_persistence_for(self, params: dict) -> DensePersistence:
        """Build a DensePersistence object, creating the embedding model record first.

        Args:
            params: Configuration parameters containing ``encoding_model``.

        Returns:
            A DensePersistence instance with matrix directories and model id.

        Raises:
            SQLAlchemyError: On embedding model DB lookup/creation failure.
        """
        enc = params.get("encoding_model", {})
        if not enc:
            return DensePersistence(matrix_dirs={}, embedding_model_id=0)
        try:
            emb_record = self._db_service.find_or_create_embedding_model(
                enc["class_name"],
                dict(sorted(enc["parameters"].items())),
            )
        except SQLAlchemyError:
            log.exception("Failed to find or create embedding model record.")
            raise
        return self._build_dense_persistence(emb_record.id)

    def _build_sparse_persistence_for(
        self, model_class: type, params: dict
    ) -> SparsePersistence:
        """Build a SparsePersistence object with a deterministic storage folder.

        The folder path is derived from a hash of class name, params, and
        chunk set id to support idempotent lookups.

        Args:
            model_class: Retriever model class.
            params: Configuration parameters.

        Returns:
            A SparsePersistence instance pointing to the computed folder.
        """
        identity = hash_function(
            json.dumps(
                {
                    "class_name": model_class.__name__,
                    "params": dict(sorted(params.items())),
                    "chunk_set_id": self._chunk_set_id,
                },
                sort_keys=True,
            )
        )[:16]
        storage_folder = os.path.join(
            self._env_RAG_path,
            "sparse_retrievers",
            f"sparse_retriever_id-{identity}",
        )
        return SparsePersistence(model_dir=storage_folder)

    def _build_dense_persistence(self, embedding_model_id: int) -> DensePersistence:
        """Build a DensePersistence with matrix directories for every document.

        Args:
            embedding_model_id: FK to the embedding model record.

        Returns:
            A DensePersistence instance with per-document matrix dirs.
        """
        matrix_dirs: dict[int, str] = {}
        for doc_id in self._chunks:
            folder = (
                f"doc_id-{doc_id}__chunk_set_id-{self._chunk_set_id}__"
                f"embedding_model_id-{embedding_model_id}"
            )
            matrix_dirs[doc_id] = os.path.join(
                self._env_RAG_path,
                "embeddings",
                folder,
            )
        return DensePersistence(
            matrix_dirs=matrix_dirs,
            embedding_model_id=embedding_model_id,
        )

    # ── Private: Persistence ───────────────────────────────────────────

    def _save_unit(self, model: RetrieverModel, sorted_params: dict[str, Any]) -> int:
        """Persist a unit retriever (dense or sparse) and return its bridge id.

        Args:
            model: The initialized retriever model.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            ValueError: If the retriever type is unsupported.
        """
        if isinstance(model, DenseRetriever):
            return self._save_dense(model, sorted_params)
        if isinstance(model, SparseRetriever):
            return self._save_sparse(model, sorted_params)
        raise ValueError(f"Unsupported retriever: {type(model).__name__}")

    def _save_dense(self, model: DenseRetriever, sorted_params: dict[str, Any]) -> int:
        """Persist a dense retriever: embedding matrices, bridge, and detail record.

        Writes any missing embedding matrices to the DB, creates a bridge
        record, and saves the dense detail sub-table row.

        Args:
            model: The initialized DenseRetriever.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            SQLAlchemyError: On any DB persistence failure.
        """
        for doc_id, mdir in model.persistence.matrix_dirs.items():
            path = os.path.join(mdir, "embeddings.npy")
            if not os.path.exists(path):
                continue
            try:
                exists = self._db_service.find_embedding_matrix(
                    doc_id,
                    self._chunk_set_id,
                    model.persistence.embedding_model_id,
                )
            except SQLAlchemyError:
                log.exception("Database error during embedding matrix lookup.")
                raise
            if exists:
                continue
            try:
                shape = list(np.load(path).shape)
            except (IOError, OSError, ValueError):
                log.warning("Could not load %s to record its shape, skipping.", path)
                continue
            try:
                self._db_service.save_embedding_matrix(
                    doc_id,
                    self._chunk_set_id,
                    model.persistence.embedding_model_id,
                    mdir,
                    shape,
                )
            except SQLAlchemyError:
                log.exception("Failed to save embedding matrix record.")
                raise

        try:
            bridge = self._db_service.create_bridge(
                model.__class__.__name__, self._pipeline_id
            )
        except SQLAlchemyError:
            log.exception("Failed to create bridge record.")
            raise
        try:
            self._db_service.save_dense(
                model.__class__.__name__,
                sorted_params,
                bridge.id,
                self._chunk_set_id,
                model.persistence.embedding_model_id,
            )
        except SQLAlchemyError:
            log.exception("Failed to save dense retriever record.")
            raise
        return bridge.id

    def _save_sparse(
        self, model: SparseRetriever, sorted_params: dict[str, Any]
    ) -> int:
        """Persist a sparse retriever: filesystem save, bridge, and detail record.

        Args:
            model: The initialized SparseRetriever.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            SQLAlchemyError: On any DB persistence failure.
        """
        model.save()

        try:
            bridge = self._db_service.create_bridge(
                model.__class__.__name__, self._pipeline_id
            )
        except SQLAlchemyError:
            log.exception("Failed to create bridge record.")
            raise
        try:
            self._db_service.save_sparse(
                model.__class__.__name__,
                sorted_params,
                model.persistence.model_dir,
                bridge.id,
                self._chunk_set_id,
            )
        except SQLAlchemyError:
            log.exception("Failed to save sparse retriever record.")
            raise
        return bridge.id
