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
from DashAI.back.models.RAG.documents.rag_document import RAGDocument
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverEmptyChildrenError,
    RAGRetrieverError,
    RAGRetrieverMissingParameterError,
)
from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence import (
    DensePersistence,
    SparsePersistence,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    strip_expansion_options,
)
from DashAI.back.models.RAG.retrievers.retriever_factory import (
    RetrieverFactory,
    resolve_component_params,
)
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever
from DashAI.back.models.RAG.utils import hash_function
from DashAI.back.services.RAG.embedding_storage_service import EmbeddingStorageService
from DashAI.back.services.RAG.retrieval_llm_service import RetrievalLLMService
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService
from DashAI.back.services.RAG.utils import build_corpus_content_hash

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrieverSetupResult:
    db_record_id: int
    model: BaseRetriever


class RetrieverSetupService:
    """Orchestrates the complete retriever lifecycle.

    Combines the pure :class:`RetrieverFactory` with database persistence
    and embedding storage so that higher-level pipeline code only needs to
    call a single ``setup()`` method per retriever configuration.

    The lifecycle is divided into three explicit phases:
        1. Construction — build the model in memory (no I/O, no DB).
           **Note:** Phase 1 includes one exception — an idempotent
           ``find_or_create_embedding_model`` call to resolve the embedding
           model id used in the :class:`DensePersistence` stub.
        2. Initialization — heavy I/O (embeddings, similarity matrices).
        3. Persistence — save to DB (bridge records, sub-table rows).

    **Composite retrievers** are never cached in the DB.  They are always
    reconstructed fresh because they are lightweight to build (their
    children are individually cached).
    """

    def __init__(
        self,
        db: Session,
        registry: ComponentRegistry,
        env_RAG_path: str,  # noqa: N803
        chunks: dict[int, dict[int, Chunk]],
        chunk_set_id: int,
        pipeline_id: int,
        chunking_key: str,
        documents: dict[int, RAGDocument] | None = None,
    ):
        """Initialize the retriever setup service.

        Internally creates :attr:`_db_service` (:class:`RetrieverDBService`)
        and :attr:`_embedding_service` (:class:`EmbeddingStorageService`).

        Args:
            db: SQLAlchemy session.
            registry: Application component registry.
            env_RAG_path: Base RAG data directory path.
            chunks: Nested dict of chunks keyed by document_id and index.
            chunk_set_id: FK to the owning chunk set. It keys this session's DB
                rows only; fitted artifacts are addressed by content, so the
                same corpus and configuration share them across chunk sets.
            pipeline_id: FK to the owning pipeline.
            chunking_key: Session-independent hash of the chunking
                configuration. Different chunking always resolves to different
                artifact folders, even if it happens to produce identical
                chunks. Required: the chunking configuration is part of every
                artifact identity.
            documents: Optional document mapping injected into the retrievers.
        """
        self._db = db
        self._registry = registry
        self._env_RAG_path = env_RAG_path
        self._chunks = chunks
        self._chunk_set_id = chunk_set_id
        self._pipeline_id = pipeline_id
        self._documents = documents
        self._chunking_key = chunking_key
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
    ) -> BaseRetriever:
        """Phase 1: Build model in memory. No I/O, no DB."""
        factory = RetrieverFactory(
            self._registry, self._env_RAG_path, self._chunks, self._documents
        )
        result = factory.create(component_name, params, persistence)
        return result.model

    def initialize_model(self, model: BaseRetriever) -> None:
        """Phase 2: Initialize model (load embeddings, similarity matrices)."""
        model.init_model()

    def persist_model(
        self, model: BaseRetriever, component_name: str, sorted_params: dict
    ) -> int:
        """Phase 3: Persist to DB and return bridge_id."""
        bridge_id = self._save_unit(model, sorted_params)
        model.set_id(bridge_id)
        return bridge_id

    def setup(
        self, component_name: str, params: dict[str, Any]
    ) -> RetrieverSetupResult:
        """Complete retriever setup: build -> initialize -> persist.

        The retrieve-then-expand options are post-processing knobs, so they are
        removed from the configuration used as the *identity* (cache lookup and
        persistence) while the live model is still built from the full
        parameters. Toggling them therefore never forces a re-index.

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

        identity_params = dict(sorted(strip_expansion_options(params).items()))
        loaded = self._load_unit_from_db(
            model_class, model_class.__name__, identity_params, params
        )
        if loaded is not None:
            return RetrieverSetupResult(db_record_id=loaded.get_id(), model=loaded)

        persistence = self._build_persistence_for(model_class, params)
        model = self.build_model(component_name, params, persistence)

        self.initialize_model(model)

        bridge_id = self.persist_model(model, component_name, identity_params)
        return RetrieverSetupResult(db_record_id=bridge_id, model=model)

    # ── Private: Composite ─────────────────────────────────────────────

    def _setup_composite(
        self, model_class: type, params: dict[str, Any]
    ) -> RetrieverSetupResult:
        """Set up a composite retriever (Sequential/Parallel) with children.

        Always builds fresh — composites are NOT cached since they are
        lightweight to reconstruct (children are individually cached).

        Args:
            model_class: The composite retriever class.
            params: Configuration parameters including ``children``.

        Returns:
            A result with the bridge DB record id and initialized model.

        Raises:
            RAGRetrieverEmptyChildrenError: If ``children`` is empty.
        """
        children_configs = params.get("children", [])
        if not children_configs:
            raise RAGRetrieverEmptyChildrenError(
                "Composite retriever must have at least one child"
            )
        children = [self._setup_child(c) for c in children_configs]
        resolved_params = resolve_component_params(
            model_class,
            {k: v for k, v in params.items() if k != "children"},
            self._registry,
            llm_resolver=self._resolve_retrieval_llm,
        )
        model = model_class(
            children=[c.model for c in children],
            **resolved_params,
        )
        model.inject_infra(self._env_RAG_path, self._chunks, None, self._documents)

        try:
            bridge = self._db_service.save_composite(
                model_class.__name__,
                self._pipeline_id,
                [c.db_record_id for c in children],
                commit=True,
            )
        except SQLAlchemyError:
            log.exception("Failed to save composite retriever.")
            raise

        model.set_id(bridge.id)
        return RetrieverSetupResult(db_record_id=bridge.id, model=model)

    def _setup_child(self, child_config: dict) -> RetrieverSetupResult:
        if "component" not in child_config or "params" not in child_config:
            raise RAGRetrieverMissingParameterError(
                f"Missing 'component' or 'params' in child config: {child_config}"
            )
        return self.setup(
            component_name=child_config["component"],
            params=child_config["params"],
        )

    def _resolve_retrieval_llm(self, component_name: str, params: dict):
        """Resolve a nested ``llm_model`` reference through the DB-backed service.

        Parameters
        ----------
        component_name : str
            Registered LLM component name.
        params : dict
            LLM constructor parameters.

        Returns
        -------
        RetrievalLLMServiceResult
            The lookup-or-create result exposing ``db_record_id`` and a lazy
            proxy for ``model``. The real backend is constructed on first use
            and released when the retriever's stage ends.
        """
        service = RetrievalLLMService(self._db, self._registry)
        return service.get_or_create_lazy(component_name, params)

    # ── Private: Unit ──────────────────────────────────────────────────

    def _load_unit_from_db(
        self,
        model_class: type,
        class_name: str,
        identity_params: dict[str, Any],
        model_params: dict[str, Any],
    ) -> BaseRetriever | None:
        """Load a unit retriever (dense or sparse) from the DB cache.

        Args:
            model_class: Retriever model class.
            class_name: Component class name string.
            identity_params: Deterministically sorted parameters without the
                retrieve-then-expand options; this is the cache key.
            model_params: Full configuration, used to build the live model so it
                keeps its expansion options.

        Returns:
            Initialized retriever model, or ``None`` if not cached.
        """
        if issubclass(model_class, DenseEmbeddingRetriever):
            return self._load_dense(class_name, identity_params, model_params)
        if issubclass(model_class, SparseRetriever):
            return self._load_sparse(class_name, identity_params, model_params)
        return None

    def _load_dense(
        self,
        class_name: str,
        identity_params: dict[str, Any],
        model_params: dict[str, Any],
    ) -> BaseRetriever | None:
        """Load a dense retriever from the DB cache by its natural key.

        Args:
            class_name: Component class name string.
            identity_params: Deterministically sorted parameters without the
                retrieve-then-expand options; this is the cache key.
            model_params: Full configuration used to build the live model.

        Returns:
            Fully initialized DenseEmbeddingRetriever, or ``None`` if not cached.

        Raises:
            SQLAlchemyError: On database lookup failure.
        """
        try:
            record = self._db_service.find_dense(
                class_name, identity_params, self._chunk_set_id
            )
        except SQLAlchemyError:
            log.exception("Database error during dense retriever lookup.")
            raise
        if record is None:
            return None
        persistence = self._build_dense_persistence(record.embedding_model_id)
        factory = RetrieverFactory(
            self._registry, self._env_RAG_path, self._chunks, self._documents
        )
        result = factory.create(class_name, dict(model_params), persistence=persistence)
        model = result.model
        model.init_model()
        bridge = self._db_service.find_bridge_for_sub_table(record, class_name)
        if bridge is not None:
            model.set_id(bridge.id)
        return model

    def _load_sparse(
        self,
        class_name: str,
        identity_params: dict[str, Any],
        model_params: dict[str, Any],
    ) -> BaseRetriever | None:
        """Load a sparse retriever from the DB cache by its natural key.

        Args:
            class_name: Component class name string.
            identity_params: Deterministically sorted parameters without the
                retrieve-then-expand options; this is the cache key.
            model_params: Full configuration used to build the live model.

        Returns:
            Fully initialized SparseRetriever, or ``None`` if not cached.

        Raises:
            SQLAlchemyError: On database lookup failure.
        """
        try:
            record = self._db_service.find_sparse(
                class_name, identity_params, self._chunk_set_id
            )
        except SQLAlchemyError:
            log.exception("Database error during sparse retriever lookup.")
            raise
        if record is None:
            return None
        persistence = SparsePersistence(model_dir=record.storage_folder)
        factory = RetrieverFactory(
            self._registry, self._env_RAG_path, self._chunks, self._documents
        )
        result = factory.create(class_name, dict(model_params), persistence=persistence)
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
        if issubclass(model_class, DenseEmbeddingRetriever):
            return self._build_dense_persistence_for(params)
        elif issubclass(model_class, SparseRetriever):
            return self._build_sparse_persistence_for(model_class, params)
        else:
            raise RAGRetrieverError(
                f"Unsupported retriever type: {model_class.__name__}"
            )

    def _build_dense_persistence_for(self, params: dict) -> DensePersistence:
        """Build a DensePersistence from the embedding model component ref.

        Reads ``params["embedding_model"]`` which at Phase 1 always has the
        schema-component format ``{"component": "<class>", "params": {...}}``,
        set by ``DenseEmbeddingRetriever.__init__``.

        When the embedding model key is absent, an empty persistence is
        returned and the caller must handle embedding computation in Phase 2.

        Args:
            params: Configuration parameters containing ``embedding_model``
                in component-ref format.

        Returns:
            A DensePersistence with matrix directories and embedding model id,
            or an empty one when no embedding model reference is present.
        """
        emb_ref = params.get("embedding_model")
        if not isinstance(emb_ref, dict):
            return DensePersistence(matrix_dirs={}, embedding_model_id=0)

        class_name = emb_ref.get("component")
        parameters = emb_ref.get("params")
        if not class_name or not isinstance(parameters, dict):
            return DensePersistence(matrix_dirs={}, embedding_model_id=0)

        try:
            emb_record = self._db_service.find_or_create_embedding_model(
                class_name,
                dict(sorted(parameters.items())),
                commit=False,
            )
        except SQLAlchemyError:
            log.exception("Failed to find or create embedding model record.")
            raise
        return self._build_dense_persistence(emb_record.id)

    def _build_sparse_persistence_for(
        self, model_class: type, params: dict
    ) -> SparsePersistence:
        """Build a SparsePersistence object with a content-addressed folder.

        The folder is derived from the retriever class, the parameters that
        actually shape the fitted matrix, and a hash of the corpus content. No
        session id, chunk-set id or chunk-set signature participates: two
        sessions over the same corpus with the same configuration share one
        fitted state, while a different corpus produces a different folder.

        Parameters excluded from the identity: the retrieve-then-expand options
        (post-processing), ``top_k`` (how many rows are returned, not how they
        are scored) and ``similarity_function`` (the distance used at query
        time). Vectorizer, ``k1``/``b``/``delta`` and the TF-IDF settings all
        stay, because changing them changes the fitted matrix.

        Args:
            model_class: Retriever model class.
            params: Configuration parameters.

        Returns:
            A SparsePersistence instance pointing to the computed folder.
        """
        artifact_params = strip_expansion_options(params)
        artifact_params.pop("top_k", None)
        artifact_params.pop("similarity_function", None)
        identity = hash_function(
            json.dumps(
                {
                    "class_name": model_class.__name__,
                    "params": dict(sorted(artifact_params.items())),
                    "corpus": build_corpus_content_hash(self._chunks),
                    "chunking": self._chunking_key,
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

        Each folder is addressed by the document's own content, so the same
        document and embedding model reuse one ``embeddings.npy`` across
        sessions and ``compute_missing_embeddings`` skips re-embedding it.

        Args:
            embedding_model_id: FK to the embedding model record.

        Returns:
            A DensePersistence instance with per-document matrix dirs.
        """
        matrix_dirs: dict[int, str] = {}
        for doc_id, document_chunks in self._chunks.items():
            content_key = hash_function(
                json.dumps(
                    {
                        "corpus": build_corpus_content_hash({doc_id: document_chunks}),
                        "chunking": self._chunking_key,
                    },
                    sort_keys=True,
                )
            )[:16]
            folder = EmbeddingStorageService.build_matrix_dir_name(
                doc_id,
                content_key,
                embedding_model_id,
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

    def _save_unit(self, model: BaseRetriever, sorted_params: dict[str, Any]) -> int:
        """Persist a unit retriever (dense or sparse) and return its bridge id.

        Args:
            model: The initialized retriever model.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            ValueError: If the retriever type is unsupported.
        """
        if isinstance(model, DenseEmbeddingRetriever):
            return self._save_dense(model, sorted_params)
        if isinstance(model, SparseRetriever):
            return self._save_sparse(model, sorted_params)
        raise ValueError(f"Unsupported retriever: {type(model).__name__}")

    def _save_dense(
        self, model: DenseEmbeddingRetriever, sorted_params: dict[str, Any]
    ) -> int:
        """Persist a dense retriever: embedding matrices, bridge, and detail record.

        All DB operations share a single transaction; the caller's session
        is committed once at the end.

        Args:
            model: The initialized DenseEmbeddingRetriever.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            SQLAlchemyError: On any DB persistence failure.
            IOError: If an embedding matrix file cannot be read.
            OSError: If an embedding matrix file cannot be read.
            ValueError: If an embedding matrix file contains invalid data.
        """
        try:
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
                except (IOError, OSError, ValueError) as exc:
                    log.error("Failed to load %s to record its shape: %s", path, exc)
                    raise

                self._db_service.save_embedding_matrix(
                    doc_id,
                    self._chunk_set_id,
                    model.persistence.embedding_model_id,
                    mdir,
                    shape,
                    commit=False,
                )

            bridge = self._db_service.create_bridge(
                model.__class__.__name__,
                self._pipeline_id,
                commit=False,
            )
            self._db_service.save_dense(
                model.__class__.__name__,
                sorted_params,
                bridge.id,
                self._chunk_set_id,
                model.persistence.embedding_model_id,
                commit=False,
            )

            self._db.commit()
        except Exception:
            self._db.rollback()
            log.exception("Failed to persist dense retriever.")
            raise

        return bridge.id

    def _save_sparse(
        self, model: SparseRetriever, sorted_params: dict[str, Any]
    ) -> int:
        """Persist a sparse retriever: filesystem save, bridge, and detail record.

        All DB operations share a single transaction; the caller's session
        is committed once at the end.

        Args:
            model: The initialized SparseRetriever.
            sorted_params: Deterministically sorted parameters.

        Returns:
            The bridge record primary key.

        Raises:
            SQLAlchemyError: On any DB persistence failure.
            IOError: If the model cannot be saved to disk.
        """
        model_dir = model.persistence.model_dir
        if model.needs_save() or not model_dir or not os.path.isdir(model_dir):
            model.save()

        try:
            bridge = self._db_service.create_bridge(
                model.__class__.__name__,
                self._pipeline_id,
                commit=False,
            )
            self._db_service.save_sparse(
                model.__class__.__name__,
                sorted_params,
                model.persistence.model_dir,
                bridge.id,
                self._chunk_set_id,
                commit=False,
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            log.exception("Failed to persist sparse retriever.")
            raise

        return bridge.id
