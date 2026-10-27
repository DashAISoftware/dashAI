import logging
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    RAGChunkingModel,
    RAGChunkSet,
    RAGChunkSetDocument,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.RAG_constants import (
    COMPOSITE_RETRIEVER_NAMES,
    RAG_PARAM_RETRIEVER_MODEL,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    strip_expansion_options,
)
from DashAI.back.services.RAG.deferred_fs import remove_after_commit, remove_now
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService

log = logging.getLogger(__name__)


def _retriever_identity(reference: Any) -> Any:
    """Return a retriever reference without its expansion options.

    The retrieve-then-expand options are post-processing knobs: they change
    nothing about what is indexed, so a session that only toggled them must not
    have its fitted retriever deleted. Stripping is recursive, so a composite's
    children are compared without their options too.

    Parameters
    ----------
    reference : Any
        A ``{"component", "params"}`` retriever reference, or any other value.

    Returns
    -------
    Any
        The reference with ``params`` stripped of the two options, or the value
        unchanged when it is not a retriever reference.
    """
    if not isinstance(reference, dict):
        return reference
    params = reference.get("params")
    if not isinstance(params, dict):
        return reference
    identity = dict(reference)
    identity["params"] = strip_expansion_options(params)
    return identity


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
                old_value = old_parameters.get(key)
                new_value = new_parameters.get(key)
                if key != RAG_PARAM_RETRIEVER_MODEL:
                    return old_value != new_value
                return _retriever_identity(old_value) != _retriever_identity(new_value)

            documents_ids = sorted(old_parameters.get("documents") or [])

            # ── Retriever cleanup (MUST run BEFORE chunking) ──
            retriever_model_params = old_parameters.get("retriever_model") or {}
            retriever_component_name = retriever_model_params.get("component", "")

            # The retriever rows deleted below hang off this session's chunk
            # set, which no other session can share now that documents belong
            # to one session. Rows keyed by configuration alone -- the chunking
            # model here, the embedding model in _cleanup_dense_retriever --
            # *are* shared, and are guarded where they are deleted.
            should_cleanup_retriever = bool(retriever_model_params) and (
                _component_changed("retriever_model")
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

            should_cleanup_chunking = bool(chunking_model_params) and (
                _component_changed("chunking_model")
            )

            if should_cleanup_chunking:
                # Ask this session's own pipeline which row it was using, rather
                # than looking one up by class name and params. Chunking rows
                # are stored with their params key-sorted while a session's
                # parameters keep whatever order the client sent, so a JSON
                # comparison silently misses the very row it means to match.
                self._drop_chunking_model_if_unused(session_id)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ── Private helpers ──

    @staticmethod
    def _delete_path(path_value: str | None) -> None:
        """Delete a filesystem path immediately, if it exists.

        Prefer queueing the path with
        :func:`~DashAI.back.services.RAG.deferred_fs.remove_after_commit` when
        it is tied to rows being deleted in a transaction.

        Args:
            path_value: Absolute path to delete. Silently skipped if
                ``None`` or the path does not exist.
        """
        remove_now(path_value)

    def _drop_chunking_model_if_unused(self, session_id: int) -> None:
        """Release the chunking model a session's pipeline points at.

        The row is shared: it is keyed by configuration, so every session that
        settled on the same chunking uses one record -- the common case, since
        a new session takes the backend defaults. It may only go once no other
        pipeline references it.

        Parameters
        ----------
        session_id : int
        """
        pipeline = (
            self.db.query(RAGPipeline).filter_by(session_id=session_id).one_or_none()
        )
        if pipeline is None or pipeline.chunking_model_id is None:
            return

        chunking_model_id = pipeline.chunking_model_id
        # Release this session's claim first, so the count below sees the truth.
        pipeline.chunking_model_id = None
        self.db.flush()

        still_used = (
            self.db.query(RAGPipeline)
            .filter(RAGPipeline.chunking_model_id == chunking_model_id)
            .count()
        )
        if still_used:
            return
        record = self.db.get(RAGChunkingModel, chunking_model_id)
        if record is not None:
            self.db.delete(record)

    def _sparse_folder_in_use(
        self, storage_folder: str, exclude_ids: Sequence[int] = ()
    ) -> bool:
        """Whether another sparse retriever row points at a storage folder.

        Sparse folders are content-addressed, so several sessions over the same
        corpus share one folder. Deleting it while another row still references
        it would break that session, so the folder may only go when the last
        reference does.

        Parameters
        ----------
        storage_folder : str
            Absolute folder path being released.
        exclude_ids : Sequence[int]
            Rows being deleted in the same transaction, which must not count as
            live references.

        Returns
        -------
        bool
            ``True`` when at least one other row still uses the folder.
        """
        query = self.db.query(RAGSparseRetriever).filter(
            RAGSparseRetriever.storage_folder == storage_folder
        )
        if exclude_ids:
            query = query.filter(RAGSparseRetriever.id.notin_(list(exclude_ids)))
        return bool(query.count())

    def _embedding_folder_in_use(
        self, storage_folder: str, exclude_ids: Sequence[int] = ()
    ) -> bool:
        """Whether another embedding matrix row points at a storage folder.

        Embedding folders are content-addressed, so every session indexing the
        same document with the same embedding model shares one folder while
        keeping its own row.

        Parameters
        ----------
        storage_folder : str
            Absolute folder path being released.
        exclude_ids : Sequence[int]
            Rows being deleted in the same transaction, which must not count as
            live references.

        Returns
        -------
        bool
            ``True`` when at least one other row still uses the folder.
        """
        query = self.db.query(RAGEmbeddingMatrix).filter(
            RAGEmbeddingMatrix.storage_folder == storage_folder
        )
        if exclude_ids:
            query = query.filter(RAGEmbeddingMatrix.id.notin_(list(exclude_ids)))
        return bool(query.count())

    def _embedding_model_in_use(
        self, embedding_model_id: int, *, exclude_dense_retriever_id: int | None = None
    ) -> bool:
        """Whether anything still references an embedding model.

        Parameters
        ----------
        embedding_model_id : int
        exclude_dense_retriever_id : int | None
            A dense retriever being deleted in the same transaction, which
            should not count as a live reference.

        Returns
        -------
        bool
        """
        retrievers = self.db.query(RAGDenseRetriever).filter(
            RAGDenseRetriever.embedding_model_id == embedding_model_id
        )
        if exclude_dense_retriever_id is not None:
            retrievers = retrievers.filter(
                RAGDenseRetriever.id != exclude_dense_retriever_id
            )
        if retrievers.count():
            return True
        return bool(
            self.db.query(RAGEmbeddingMatrix)
            .filter(RAGEmbeddingMatrix.embedding_model_id == embedding_model_id)
            .count()
        )

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
                    detail = child_bridge.sparse_detail
                    if not self._sparse_folder_in_use(
                        detail.storage_folder, exclude_ids=[detail.id]
                    ):
                        remove_after_commit(self.db, detail.storage_folder)
                    self.db.delete(detail)
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

        matrix_ids = [matrix.id for matrix in embedding_matrices]
        for matrix in embedding_matrices:
            if not self._embedding_folder_in_use(
                matrix.storage_folder, exclude_ids=matrix_ids
            ):
                self._delete_path(matrix.storage_folder)

        if matrix_ids:
            self.db.query(RAGEmbeddingMatrix).filter(
                RAGEmbeddingMatrix.id.in_(matrix_ids)
            ).delete(synchronize_session="fetch")

        # Embedding models are also keyed by configuration alone, so another
        # session's dense retriever or embedding matrix may still need this row.
        embedding_model = self.db.get(RAGEmbeddingModel, embedding_model_id)
        if embedding_model is not None and not self._embedding_model_in_use(
            embedding_model_id, exclude_dense_retriever_id=dense_retriever.id
        ):
            self.db.delete(embedding_model)

        self.db.delete(dense_retriever)

    def _cleanup_sparse_retriever(
        self,
        bridge: RAGRetriever,
    ) -> None:
        """Cascade-delete a sparse retriever and its storage folder.

        Removes the sparse detail DB record and, when no other row shares it,
        the on-disk storage folder: folders are content-addressed, so another
        session may still be using this one.

        Args:
            bridge: The bridge record for the sparse retriever.
        """
        sparse_retriever = bridge.sparse_detail
        if not self._sparse_folder_in_use(
            sparse_retriever.storage_folder, exclude_ids=[sparse_retriever.id]
        ):
            self._delete_path(sparse_retriever.storage_folder)
        self.db.delete(sparse_retriever)

    def invalidate_session_artifacts(
        self, session_id: int, *, commit: bool = True
    ) -> None:
        """Delete every chunk set a session owns, with what was fitted on it.

        Chunk sets carry their owning ``session_id``, so this never reaches the
        index of another session, even one using the same Data documents.

        Parameters
        ----------
        session_id : int
            The generative session whose indexes are discarded.
        commit : bool
            When ``False`` the caller owns the transaction and commits it.
        """
        chunk_set_ids = [
            row[0]
            for row in self.db.query(RAGChunkSet.id)
            .filter(RAGChunkSet.session_id == session_id)
            .all()
        ]
        for chunk_set_id in chunk_set_ids:
            self._invalidate_chunk_set(chunk_set_id)
        if commit:
            self.db.commit()

    def invalidate_legacy_artifacts(self, *, commit: bool = True) -> int:
        """Delete the chunk sets that have no owning session.

        Migration d8f3a1c6e2b9 detaches every chunk set that existed before
        chunks became Arrow documents, and older ones indexed rows of the
        legacy ``document`` table. None of them can be used again, so this
        removes their rows and folders at startup.

        Parameters
        ----------
        commit : bool
            When ``False`` the caller owns the transaction and commits it.

        Returns
        -------
        int
            Number of chunk sets deleted.
        """
        chunk_set_ids = [
            row[0]
            for row in self.db.query(RAGChunkSet.id)
            .filter(RAGChunkSet.session_id.is_(None))
            .all()
        ]
        for chunk_set_id in chunk_set_ids:
            self._invalidate_chunk_set(chunk_set_id)
        if commit:
            self.db.commit()
        return len(chunk_set_ids)

    def _invalidate_chunk_set(self, chunk_set_id: int) -> None:
        """Delete one chunk set and everything fitted on it.

        Removes the composite retrievers built over its retrievers, its sparse
        and dense retrievers, its embedding matrices (and their embedding model
        once nothing else uses it) and the chunk set itself, whose chunks and
        membership rows go with it. Storage folders are content-addressed, so a
        folder is only queued with ``remove_after_commit`` once no other row
        still references it.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set to delete.
        """
        document_ids = [
            row[0]
            for row in self.db.query(RAGChunkSetDocument.document_id)
            .filter(RAGChunkSetDocument.chunk_set_id == chunk_set_id)
            .all()
        ]
        sparse_links = (
            self.db.query(RAGSparseRetriever, RAGRetriever)
            .join(RAGRetriever, RAGSparseRetriever.bridge_id == RAGRetriever.id)
            .filter(RAGSparseRetriever.chunk_set_id == chunk_set_id)
            .all()
        )
        dense_links = (
            self.db.query(RAGDenseRetriever, RAGRetriever)
            .join(RAGRetriever, RAGDenseRetriever.bridge_id == RAGRetriever.id)
            .filter(RAGDenseRetriever.chunk_set_id == chunk_set_id)
            .all()
        )

        child_bridge_ids = {bridge.id for _, bridge in sparse_links + dense_links}
        if child_bridge_ids:
            parent_ids = {
                link.parent_id
                for link in self.db.query(RAGRetrieverChild)
                .filter(RAGRetrieverChild.child_id.in_(child_bridge_ids))
                .all()
            }
            for parent_id in parent_ids:
                parent = self.db.get(RAGRetriever, parent_id)
                if parent is not None:
                    self.db.delete(parent)

        sparse_ids = [detail.id for detail, _bridge in sparse_links]

        for sparse_detail, bridge in sparse_links:
            if not self._sparse_folder_in_use(
                sparse_detail.storage_folder, exclude_ids=sparse_ids
            ):
                remove_after_commit(self.db, sparse_detail.storage_folder)
            self.db.delete(sparse_detail)
            self.db.delete(bridge)

        dense_matrices: dict[int, list[RAGEmbeddingMatrix]] = {}
        for dense_detail, _bridge in dense_links:
            dense_matrices[dense_detail.id] = (
                self.db.query(RAGEmbeddingMatrix)
                .filter(
                    RAGEmbeddingMatrix.chunk_set_id == chunk_set_id,
                    RAGEmbeddingMatrix.embedding_model_id
                    == dense_detail.embedding_model_id,
                    RAGEmbeddingMatrix.document_id.in_(document_ids),
                )
                .all()
            )
        doomed_matrix_ids = [
            matrix.id for matrices in dense_matrices.values() for matrix in matrices
        ]

        for dense_detail, bridge in dense_links:
            embedding_model_id = dense_detail.embedding_model_id
            for matrix in dense_matrices[dense_detail.id]:
                if not self._embedding_folder_in_use(
                    matrix.storage_folder, exclude_ids=doomed_matrix_ids
                ):
                    remove_after_commit(self.db, matrix.storage_folder)
                self.db.delete(matrix)
            if not self._embedding_model_in_use(
                embedding_model_id, exclude_dense_retriever_id=dense_detail.id
            ):
                embedding_model = self.db.get(RAGEmbeddingModel, embedding_model_id)
                if embedding_model is not None:
                    self.db.delete(embedding_model)
            self.db.delete(dense_detail)
            self.db.delete(bridge)

        chunk_folders = {
            str(Path(row[0]).parent)
            for row in self.db.query(RAGChunkSetDocument.path)
            .filter(
                RAGChunkSetDocument.chunk_set_id == chunk_set_id,
                RAGChunkSetDocument.path.isnot(None),
            )
            .all()
        }
        for folder in chunk_folders:
            remove_after_commit(self.db, folder)
        chunk_set = self.db.get(RAGChunkSet, chunk_set_id)
        if chunk_set is not None:
            self.db.delete(chunk_set)
