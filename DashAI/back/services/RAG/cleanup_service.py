import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from sqlalchemy.orm import Session

from DashAI.back.core.schema_fields.utils import normalize_payload
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
from DashAI.back.models.RAG.exceptions import RAGPipelineConfigError
from DashAI.back.models.RAG.RAG_constants import (
    CHILDREN_KEY,
    COMPONENT_KEY,
    COMPOSITE_RETRIEVER_NAMES,
    PARAMS_KEY,
    RAG_PARAM_QUERY_TRANSFORMATION,
    RAG_PARAM_RETRIEVER_MODEL,
    RERANKER_KEY,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    strip_expansion_options,
)
from DashAI.back.services.RAG.deferred_fs import remove_after_commit
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
    params = reference.get(PARAMS_KEY)
    if not isinstance(params, dict):
        return reference
    identity = dict(reference)
    identity[PARAMS_KEY] = strip_expansion_options(params)
    return identity


def _reranker_reference(
    parameters: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Return the query-transformation reranker reference of session parameters.

    Parameters
    ----------
    parameters : Optional[Dict[str, Any]]
        A session's parameters dict, or ``None``.

    Returns
    -------
    Optional[Dict[str, Any]]
        The ``reranker`` reference nested in ``query_transformation``, or
        ``None`` when the stage, its params or the reranker is absent (the
        stage is optional and so is its reranker).

    Raises
    ------
    RAGPipelineConfigError
        If a reranker is stored but is not a component reference.
    """
    if not parameters:
        return None
    transformation = parameters.get(RAG_PARAM_QUERY_TRANSFORMATION)
    if not transformation:
        return None
    params = transformation.get(PARAMS_KEY)
    if not params:
        return None
    reranker = params.get(RERANKER_KEY)
    if reranker is None:
        return None
    return _require_reference(reranker, "the query transformation reranker")


def _require_reference(value: Any, what: str) -> Dict[str, Any]:
    """Return ``value`` when it is a component reference, or raise.

    Parameters
    ----------
    value : Any
        A stored reference.
    what : str
        What the reference is, for the error message.

    Returns
    -------
    Dict[str, Any]
        The reference, unchanged.

    Raises
    ------
    RAGPipelineConfigError
        If ``value`` is not a dict carrying a ``component``.
    """
    if not isinstance(value, dict) or COMPONENT_KEY not in value:
        raise RAGPipelineConfigError(
            f"Stored configuration of {what} is not a component reference."
        )
    return value


def _reference_params(reference: Dict[str, Any]) -> Dict[str, Any]:
    """Return a reference's normalized ``params``.

    A reference without ``params`` is the minimal ``{"component": name}`` the
    form stores for a component chosen by name alone, so it has no parameters.

    Parameters
    ----------
    reference : Dict[str, Any]
        A component reference.

    Returns
    -------
    Dict[str, Any]
        The normalized parameters, empty for the minimal reference.

    Raises
    ------
    RAGPipelineConfigError
        If ``params`` is present and not a dict.
    """
    params = reference.get(PARAMS_KEY)
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise RAGPipelineConfigError(
            f"'params' of stored component '{reference[COMPONENT_KEY]}' is not a dict."
        )
    return normalize_payload(params)


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
        old_parameters: Dict[str, Any],
        new_parameters: Optional[Dict[str, Any]] = None,
        *,
        commit: bool = True,
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
            commit: Whether to commit the current transaction. The bulk
                cascade paths pass ``False`` so several sessions and their
                document are deleted atomically by the caller.
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

            # The retriever stage and the query-transformation reranker store
            # their rows under the same pipeline, and one row can serve both
            # when they share a configuration. Whatever the new parameters still
            # reference must survive the cleanup of the other stage.
            protected = self._protected_bridge_ids(session_id, new_parameters)

            if should_cleanup_retriever:
                if retriever_component_name in COMPOSITE_RETRIEVER_NAMES:
                    self._cleanup_composite_retriever(
                        old_parameters, session_id, protected
                    )
                else:
                    self._cleanup_unit_retriever(
                        old_parameters,
                        documents_ids,
                        retriever_model_params,
                        session_id,
                        protected,
                    )

            old_reranker = _reranker_reference(old_parameters)
            if old_reranker is not None and (
                new_parameters is None
                or _retriever_identity(old_reranker)
                != _retriever_identity(_reranker_reference(new_parameters))
            ):
                self._cleanup_reranker(
                    old_reranker, documents_ids, session_id, protected
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

            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ── Private helpers ──

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

    def _select_unit_bridge(
        self, pipeline_id: int, reference: Dict[str, Any], protected: Set[int]
    ) -> Optional[RAGRetriever]:
        """Pick the bridge row that realizes a unit retriever reference.

        The row whose stored parameters equal the reference is preferred. A
        pipeline also holds the reranker's rows, which can share the class name,
        so a lookup by class name alone could return the wrong one; it is only
        the fallback for rows whose parameters no longer match, and it never
        returns a protected row.

        Args:
            pipeline_id: The owning pipeline.
            reference: The ``{component, params}`` retriever reference.
            protected: Bridge ids that must not be selected.

        Returns:
            The bridge to delete, or ``None`` when there is none.
        """
        for bridge in self._matching_bridges(pipeline_id, reference):
            if bridge.id not in protected:
                return bridge
        candidates = (
            self.db.query(RAGRetriever)
            .filter(
                RAGRetriever.pipeline_id == pipeline_id,
                RAGRetriever.class_name == reference[COMPONENT_KEY],
            )
            .order_by(RAGRetriever.id)
            .all()
        )
        for bridge in candidates:
            if bridge.id not in protected:
                return bridge
        return None

    def _matching_bridges(
        self, pipeline_id: int, reference: Dict[str, Any]
    ) -> List[RAGRetriever]:
        """Return the bridges that realize a retriever reference exactly.

        Args:
            pipeline_id: The owning pipeline.
            reference: A ``{component, params}`` retriever reference.

        Returns:
            Bridges of the referenced class whose stored parameters (unit) or
            ordered children (composite) match the reference.

        Raises:
            RAGPipelineConfigError: If the reference or one of its children is
                malformed.
        """
        component = reference[COMPONENT_KEY]
        params = _reference_params(reference)
        candidates = (
            self.db.query(RAGRetriever)
            .filter(
                RAGRetriever.pipeline_id == pipeline_id,
                RAGRetriever.class_name == component,
            )
            .all()
        )
        matches: List[RAGRetriever] = []
        for bridge in candidates:
            if self._bridge_matches(bridge, component, params):
                matches.append(bridge)
        return matches

    def _bridge_matches(
        self, bridge: RAGRetriever, component: str, params: Dict[str, Any]
    ) -> bool:
        """Check whether a bridge row realizes a component with these params.

        Args:
            bridge: The candidate bridge row.
            component: The referenced component name.
            params: The referenced, normalized parameters.

        Returns:
            ``True`` when a unit's stored parameters equal the reference
            (ignoring the expansion options), or when a composite's ordered
            children match the referenced children recursively.

        Raises:
            RAGPipelineConfigError: If a composite reference has no list of
                children, or one of its children is not a component reference.
        """
        if component in COMPOSITE_RETRIEVER_NAMES:
            child_refs = params.get(CHILDREN_KEY)
            if not isinstance(child_refs, list):
                raise RAGPipelineConfigError(
                    f"Stored composite retriever '{component}' has no list of children."
                )
            links = sorted(bridge.children, key=lambda link: link.child_order)
            if len(links) != len(child_refs):
                return False
            for link, child_ref in zip(links, child_refs, strict=True):
                child_ref = _require_reference(
                    child_ref, f"a child of the composite retriever '{component}'"
                )
                child = self.db.get(RAGRetriever, link.child_id)
                child_name = child_ref[COMPONENT_KEY]
                if child is None or child.class_name != child_name:
                    return False
                child_params = _reference_params(child_ref)
                if not self._bridge_matches(child, child_name, child_params):
                    return False
            return True
        detail = bridge.dense_detail or bridge.sparse_detail
        if detail is None:
            return False
        identity = dict(sorted(strip_expansion_options(params).items()))
        return detail.parameters == identity

    def _tree_ids(self, bridge: RAGRetriever) -> Set[int]:
        """Return the id of a bridge and of every descendant child bridge.

        Args:
            bridge: The root bridge row.

        Returns:
            The ids of the whole retriever tree.
        """
        ids = {bridge.id}
        for link in bridge.children:
            child = self.db.get(RAGRetriever, link.child_id)
            if child is not None:
                ids |= self._tree_ids(child)
        return ids

    def _protected_bridge_ids(
        self, session_id: int, new_parameters: Optional[Dict[str, Any]]
    ) -> Set[int]:
        """Collect the bridge rows the session's new parameters still use.

        The retriever stage and the reranker keep their rows under one
        pipeline, and a row serves both when their configurations are equal.
        Deleting the old rows of one stage must not take the other stage's.

        Args:
            session_id: Generative session identifier.
            new_parameters: The parameters after the change, or ``None`` when
                the session is being deleted (nothing is protected).

        Returns:
            The ids of every bridge in the trees the new parameters reference.

        Raises:
            RAGPipelineConfigError: If a stored reference is malformed.
        """
        if new_parameters is None:
            return set()
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return set()
        retriever = new_parameters.get(RAG_PARAM_RETRIEVER_MODEL)
        references: List[Dict[str, Any]] = []
        if retriever is not None:
            references.append(_require_reference(retriever, "the retriever"))
        reranker = _reranker_reference(new_parameters)
        if reranker is not None:
            references.append(reranker)
        protected: Set[int] = set()
        for reference in references:
            for bridge in self._matching_bridges(pipeline_id, reference):
                protected |= self._tree_ids(bridge)
        return protected

    def _cleanup_reranker(
        self,
        reference: Dict[str, Any],
        documents_ids: List[int],
        session_id: int,
        protected: Set[int],
    ) -> None:
        """Delete the rows the query-transformation reranker owned.

        Only rows that match the old reranker reference exactly are removed, so
        the retriever stage's rows are never swept by class name.

        Args:
            reference: The old ``{component, params}`` reranker reference.
            documents_ids: Document ids whose embeddings to delete.
            session_id: Generative session identifier.
            protected: Bridge ids the session's new parameters still use.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return
        for bridge in self._matching_bridges(pipeline_id, reference):
            if bridge.id not in protected:
                self._delete_bridge_tree(bridge, documents_ids, protected)

    def _delete_bridge_tree(
        self, bridge: RAGRetriever, documents_ids: List[int], protected: Set[int]
    ) -> None:
        """Delete a bridge, its descendants and the resources they own.

        Args:
            bridge: The root bridge row.
            documents_ids: Document ids whose embeddings to delete.
            protected: Bridge ids that must survive.
        """
        for link in list(bridge.children):
            child = self.db.get(RAGRetriever, link.child_id)
            if child is not None and child.id not in protected:
                self._delete_bridge_tree(child, documents_ids, protected)
        if bridge.dense_detail is not None:
            self._cleanup_dense_retriever(bridge, documents_ids, protected)
        elif bridge.sparse_detail is not None:
            self._cleanup_sparse_retriever(bridge)
        self.db.delete(bridge)

    def _find_pipeline_id(self, session_id: int) -> Optional[int]:
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
        old_parameters: Dict[str, Any],
        session_id: int,
        protected: Set[int],
    ) -> None:
        """Cascade-delete a composite retriever and its children.

        The composite is found by its stored shape, like a unit retriever: the
        bridges of the old reference's class whose ordered children match the
        reference. Only when none matches does the cleanup fall back to
        sweeping every unprotected bridge of that class. That fallback exists
        for rows whose stored children no longer equal the saved reference (for
        example the duplicates the setup inserted every turn before composite
        rows were reused), and its limit is that it cannot tell such a row from
        another stage's row of the same class; protected rows are never swept.

        Then recursively deletes child retrievers (sparse detail storage
        folders, dense detail records) and removes the parent bridge record.

        Args:
            old_parameters: Session parameters containing the retriever
                reference.
            session_id: Generative session identifier.
            protected: Bridge ids the session's new parameters still use; they
                are never deleted, even when they share this class name.

        Raises:
            RAGPipelineConfigError: If the stored retriever reference is
                malformed.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return

        reference = _require_reference(
            old_parameters[RAG_PARAM_RETRIEVER_MODEL], "the retriever"
        )

        composite_bridges = [
            bridge
            for bridge in self._matching_bridges(pipeline_id, reference)
            if bridge.id not in protected
        ]
        if not composite_bridges:
            composite_bridges = (
                self.db.query(RAGRetriever)
                .filter(
                    RAGRetriever.pipeline_id == pipeline_id,
                    RAGRetriever.class_name == reference[COMPONENT_KEY],
                    RAGRetriever.id.notin_(list(protected)),
                )
                .order_by(RAGRetriever.id)
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
                if child_bridge is None or child_bridge.id in protected:
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
        old_parameters: Dict[str, Any],
        documents_ids: List[int],
        retriever_model_params: Dict[str, Any],
        session_id: int,
        protected: Set[int],
    ) -> None:
        """Cascade-delete a unit retriever (dense or sparse).

        Determines retriever type by inspecting the bridge relationship
        (``dense_detail`` vs ``sparse_detail``) rather than parameter heuristics.

        Args:
            old_parameters: Session parameters dict.
            documents_ids: Document ids associated with the session.
            retriever_model_params: The ``retriever_model`` parameter dict.
            session_id: Generative session identifier.
            protected: Bridge ids the session's new parameters still use.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return

        bridge = self._select_unit_bridge(
            pipeline_id, retriever_model_params, protected
        )
        if bridge is None:
            return

        if bridge.dense_detail is not None:
            self._cleanup_dense_retriever(bridge, documents_ids, protected)
        elif bridge.sparse_detail is not None:
            self._cleanup_sparse_retriever(bridge)
        self.db.delete(bridge)

    def _matrices_used_by_protected(
        self, dense_retriever: RAGDenseRetriever, protected: Set[int]
    ) -> bool:
        """Whether a protected dense retriever shares this one's matrices.

        Embedding matrices are keyed by chunk set, embedding model and document,
        not by retriever, so two dense retrievers with the same embedding over
        the same chunks (a retriever and a reranker that differ only in
        ``top_k``) read the same matrices.

        Args:
            dense_retriever: The dense detail being deleted.
            protected: Bridge ids the session's new parameters still use.

        Returns:
            ``True`` when a protected dense retriever uses the same chunk set and
            embedding model, so the matrices must stay.
        """
        if not protected:
            return False
        return bool(
            self.db.query(RAGDenseRetriever)
            .filter(
                RAGDenseRetriever.bridge_id.in_(list(protected)),
                RAGDenseRetriever.id != dense_retriever.id,
                RAGDenseRetriever.chunk_set_id == dense_retriever.chunk_set_id,
                RAGDenseRetriever.embedding_model_id
                == dense_retriever.embedding_model_id,
            )
            .count()
        )

    def _cleanup_dense_retriever(
        self,
        bridge: RAGRetriever,
        documents_ids: List[int],
        protected: Set[int],
    ) -> None:
        """Cascade-delete a dense retriever and its embedding resources.

        Removes embedding matrix storage folders, deletes matrix DB records,
        the embedding model record, and the dense detail record. The matrices
        stay when a protected dense retriever still reads them (see
        :meth:`_matrices_used_by_protected`).

        Args:
            bridge: The bridge record for the dense retriever.
            documents_ids: Document ids whose embeddings to delete.
            protected: Bridge ids the session's new parameters still use.
        """
        dense_retriever = bridge.dense_detail
        chunk_set_id = dense_retriever.chunk_set_id
        embedding_model_id = dense_retriever.embedding_model_id

        if self._matrices_used_by_protected(dense_retriever, protected):
            embedding_matrices: List[RAGEmbeddingMatrix] = []
        else:
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
                remove_after_commit(self.db, matrix.storage_folder)

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
            remove_after_commit(self.db, sparse_retriever.storage_folder)
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
