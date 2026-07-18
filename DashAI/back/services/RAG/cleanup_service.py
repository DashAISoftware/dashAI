import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGChunkingModel,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
)
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService

log = logging.getLogger(__name__)

COMPOSITE_RETRIEVER_NAMES = frozenset({"SequentialRetriever", "ParallelRetriever"})


class CleanupService:
    """Cascade deletion of RAG resources when a session is deleted or updated.

    Responsible for removing orphaned retriever models, chunking models,
    embedding matrices, and storage folders when a generative session is
    deleted or its parameters are updated. Order of operations is critical:
    retrievers must be cleaned up BEFORE chunking models.
    """

    def __init__(self, db: Session):
        self.db = db
        self._retriever_db = RetrieverDBService(db)

    def cleanup_orphaned_resources(
        self,
        session_id: int,
        old_parameters: dict,
        new_parameters: dict | None = None,
    ) -> None:
        """Main entry point. Called on session DELETE or parameter UPDATE.

        Order MUST be: retriever cleanup BEFORE chunking cleanup.
        (Retriever cleanup queries chunking_model_id from DB — if chunking
        models are deleted first, the query returns None.)

        Args:
            session_id: The generative session being deleted or updated.
            old_parameters: The session's parameters before the change.
            new_parameters: The session's parameters after the change, or
                ``None`` on full session deletion.
        """
        try:
            if not old_parameters:
                return

            def _component_changed(key: str) -> bool:
                if new_parameters is None:
                    return True
                return old_parameters.get(key) != new_parameters.get(key)

            documents_ids = sorted(old_parameters.get("documents") or [])

            # ── Retriever cleanup (MUST run BEFORE chunking) ──
            retriever_model_params = old_parameters.get("retriever_model") or {}
            retriever_component_name = retriever_model_params.get("component", "")

            should_cleanup_retriever = (
                bool(retriever_model_params)
                and _component_changed("retriever_model")
                and not self._other_sessions_with_same_config(
                    session_id,
                    old_parameters,
                    keys=("documents", "chunking_model", "retriever_model"),
                )
            )

            if should_cleanup_retriever:
                if retriever_component_name in COMPOSITE_RETRIEVER_NAMES:
                    self._cleanup_composite_retriever(old_parameters, session_id)
                else:
                    self._cleanup_unit_retriever(
                        old_parameters,
                        documents_ids,
                        retriever_model_params,
                        session_id,
                    )

            # ── Chunking model cleanup (AFTER retriever) ──
            chunking_model_params = old_parameters.get("chunking_model") or {}

            should_cleanup_chunking = (
                bool(chunking_model_params)
                and _component_changed("chunking_model")
                and not self._other_sessions_with_same_config(
                    session_id,
                    old_parameters,
                    keys=("documents", "chunking_model"),
                )
            )

            if should_cleanup_chunking:
                chunking_models = (
                    self.db.query(RAGChunkingModel)
                    .filter(
                        RAGChunkingModel.class_name
                        == chunking_model_params.get("component"),
                        RAGChunkingModel.parameters
                        == chunking_model_params.get("params"),
                    )
                    .all()
                )
                for chunking_model in chunking_models:
                    self.db.delete(chunking_model)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ── Private helpers ──

    @staticmethod
    def _delete_path(path_value: str | None) -> None:
        """Delete a filesystem path recursively if it exists.

        Logs a warning if deletion fails (e.g. permission error, file in use).

        Args:
            path_value: Absolute path to delete. Silently skipped if
                ``None`` or the path does not exist.
        """
        if not path_value:
            return
        path = Path(path_value)
        if path.exists():
            try:
                shutil.rmtree(path)
            except OSError as exc:
                log.warning("Failed to remove %s: %s", path_value, exc)

    def _other_sessions_with_same_config(
        self,
        session_id: int,
        expected_parameters: dict,
        *,
        keys: tuple[str, ...],
    ) -> bool:
        """Return True if any other session matches all specified keys.

        Used to avoid deleting shared resources that another session still
        depends on.

        Args:
            session_id: Current session id (excluded from the check).
            expected_parameters: Parameter dict to compare against.
            keys: Subset of keys to compare for equality.

        Returns:
            True if at least one other session shares the same config values
            for all specified keys.
        """
        other_sessions = (
            self.db.query(GenerativeSession)
            .filter(GenerativeSession.id != session_id)
            .all()
        )
        for other_session in other_sessions:
            other_params = other_session.parameters or {}
            if all(other_params.get(k) == expected_parameters.get(k) for k in keys):
                return True
        return False

    def _find_pipeline_id(self, session_id: int) -> int | None:
        """Find pipeline DB record ID for a session.

        Args:
            session_id: Generative session identifier.

        Returns:
            The pipeline record id, or ``None`` if no pipeline exists.
        """
        pipeline = self.db.query(RAGPipeline).filter_by(session_id=session_id).first()
        return pipeline.id if pipeline else None

    def _cleanup_composite_retriever(
        self,
        old_parameters: dict,
        session_id: int,
    ) -> None:
        """Cascade-delete a composite retriever and its children.

        Finds the composite bridge record, recursively deletes child
        retrievers (sparse detail storage folders, dense detail records),
        then removes the parent bridge record.

        Args:
            old_parameters: Session parameters containing the retriever
                component name.
            session_id: Generative session identifier.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return

        retriever_component_name = old_parameters.get("retriever_model", {}).get(
            "component"
        )

        composite_bridges = (
            self.db.query(RAGRetriever)
            .filter(
                RAGRetriever.pipeline_id == pipeline_id,
                RAGRetriever.class_name == retriever_component_name,
            )
            .all()
        )

        for bridge in composite_bridges:
            child_links = (
                self.db.query(RAGRetrieverChild)
                .filter_by(parent_id=bridge.id)
                .order_by(RAGRetrieverChild.child_order)
                .all()
            )
            for link in child_links:
                child_bridge = self.db.query(RAGRetriever).get(link.child_id)
                if child_bridge is None:
                    continue
                if child_bridge.sparse_detail:
                    self._delete_path(child_bridge.sparse_detail.storage_folder)
                    self.db.delete(child_bridge.sparse_detail)
                elif child_bridge.dense_detail:
                    self.db.delete(child_bridge.dense_detail)
            self.db.delete(bridge)

    def _cleanup_unit_retriever(
        self,
        old_parameters: dict,
        documents_ids: list,
        retriever_model_params: dict,
        session_id: int,
    ) -> None:
        """Cascade-delete a unit retriever (dense or sparse).

        Determines retriever type by inspecting the bridge relationship
        (``dense_detail`` vs ``sparse_detail``) rather than parameter heuristics.

        Args:
            old_parameters: Session parameters dict.
            documents_ids: Document ids associated with the session.
            retriever_model_params: The ``retriever_model`` parameter dict.
            session_id: Generative session identifier.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return

        bridge = (
            self.db.query(RAGRetriever)
            .filter(
                RAGRetriever.pipeline_id == pipeline_id,
                RAGRetriever.class_name == retriever_model_params.get("component"),
            )
            .first()
        )
        if bridge is None:
            return

        if bridge.dense_detail is not None:
            self._cleanup_dense_retriever(bridge, documents_ids)
        elif bridge.sparse_detail is not None:
            self._cleanup_sparse_retriever(bridge)
        self.db.delete(bridge)

    def _cleanup_dense_retriever(
        self,
        bridge: RAGRetriever,
        documents_ids: list,
    ) -> None:
        """Cascade-delete a dense retriever and its embedding resources.

        Removes embedding matrix storage folders, deletes matrix DB records,
        the embedding model record, and the dense detail record.

        Args:
            bridge: The bridge record for the dense retriever.
            documents_ids: Document ids whose embeddings to delete.
        """
        dense_retriever = bridge.dense_detail
        chunk_set_id = dense_retriever.chunk_set_id
        embedding_model_id = dense_retriever.embedding_model_id

        embedding_matrices = (
            self.db.query(RAGEmbeddingMatrix)
            .filter(
                RAGEmbeddingMatrix.chunk_set_id == chunk_set_id,
                RAGEmbeddingMatrix.embedding_model_id == embedding_model_id,
                RAGEmbeddingMatrix.document_id.in_(documents_ids),
            )
            .all()
        )

        matrix_ids = []
        for matrix in embedding_matrices:
            self._delete_path(matrix.storage_folder)
            matrix_ids.append(matrix.id)

        if matrix_ids:
            self.db.query(RAGEmbeddingMatrix).filter(
                RAGEmbeddingMatrix.id.in_(matrix_ids)
            ).delete(synchronize_session="fetch")

        embedding_model = self.db.query(RAGEmbeddingModel).get(embedding_model_id)
        if embedding_model is not None:
            self.db.delete(embedding_model)

        self.db.delete(dense_retriever)

    def _cleanup_sparse_retriever(
        self,
        bridge: RAGRetriever,
    ) -> None:
        """Cascade-delete a sparse retriever and its storage folder.

        Removes the on-disk storage folder and the sparse detail DB record.

        Args:
            bridge: The bridge record for the sparse retriever.
        """
        sparse_retriever = bridge.sparse_detail
        self._delete_path(sparse_retriever.storage_folder)
        self.db.delete(sparse_retriever)
