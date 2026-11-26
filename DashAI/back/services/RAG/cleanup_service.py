import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import select
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
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.exceptions import RAGComponentNotFoundError
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PARAM_CHUNKING_MODEL,
    RAG_PARAM_RETRIEVER_MODEL,
)
from DashAI.back.models.RAG.retrievers.persistence_signature import (
    reference_signature,
)
from DashAI.back.models.RAG.retrievers.ref_utils import COMPONENT_KEY, is_component_ref
from DashAI.back.services.RAG.config_equality import configs_equal
from DashAI.back.services.RAG.deferred_fs import remove_after_commit
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService
from DashAI.back.services.RAG.storage_layout import (
    CHUNK_SETS_DIRNAME,
    EMBEDDINGS_DIRNAME,
    SPARSE_RETRIEVERS_DIRNAME,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexCleanupSummary:
    """Counts of what :meth:`CleanupService.cleanup_after_reindex` released.

    Attributes
    ----------
    chunk_sets : int
        Stale chunk sets of the session that were invalidated.
    bridges : int
        Stale retriever bridges of the session's pipeline that were released,
        composites and unit retrievers alike. Bridges removed with an
        invalidated chunk set are not counted here.
    embedding_matrices : int
        Embedding matrices of the live chunk set that no live retriever uses.
    embedding_models : int
        Embedding models left unused by the release and deleted.
    """

    chunk_sets: int
    bridges: int
    embedding_matrices: int
    embedding_models: int


@dataclass(frozen=True)
class _LiveIndex:
    """The validated live index of a session after a successful reindex.

    Attributes
    ----------
    pipeline_id : int
        The session's pipeline, which owns every bridge of the index.
    root_id : int
        The bridge the reindex returned, which roots the live tree.
    chunk_set_id : int
        The chunk set the live retrievers read, owned by the session.
    dense_model_ids : frozenset[int]
        Embedding models used by the live dense retrievers.
    """

    pipeline_id: int
    root_id: int
    chunk_set_id: int
    dense_model_ids: frozenset[int]


@dataclass(frozen=True)
class _LiveLeaves:
    """The chunk set and embedding models that the leaves of a live tree read.

    Attributes
    ----------
    chunk_set_id : int
        The one chunk set every leaf reads.
    dense_model_ids : frozenset[int]
        Embedding models of the dense leaves.
    """

    chunk_set_id: int
    dense_model_ids: frozenset[int]


@dataclass(frozen=True)
class _BridgeRelease:
    """What the release of a set of bridge trees deleted.

    Attributes
    ----------
    bridges : int
        Bridges deleted, composites and leaves alike.
    dense_leaves : frozenset[tuple[int, int]]
        ``(chunk set id, embedding model id)`` of every dense leaf deleted. The
        caller decides which matrices and models those leaves left unused.
    """

    bridges: int
    dense_leaves: frozenset[tuple[int, int]]

    @property
    def model_ids(self) -> frozenset[int]:
        """Embedding models the deleted dense leaves used."""
        return frozenset(_model_ids_of(self.dense_leaves))


def _model_ids_of(pairs: Iterable[tuple[int, int]]) -> set[int]:
    """Return the embedding model ids of ``(chunk set id, model id)`` pairs.

    Parameters
    ----------
    pairs : Iterable[tuple[int, int]]
        Pairs of a chunk set id and an embedding model id.

    Returns
    -------
    set[int]
        The model ids, without repeats.
    """
    model_ids: set[int] = set()
    for _chunk_set_id, model_id in pairs:
        model_ids.add(model_id)
    return model_ids


@dataclass(frozen=True)
class _MatrixRelease:
    """What :meth:`CleanupService._release_unused_matrices` released.

    Attributes
    ----------
    matrices : int
        Embedding matrices of the live chunk set deleted.
    models : int
        Embedding models deleted because nothing references them any more.
    """

    matrices: int
    models: int


def _retriever_identity(reference: Any, registry: ComponentRegistry | None) -> Any:
    """Return a retriever reference reduced to its persistence signature.

    Query-time parameters (``top_k``, the distance metric, the
    retrieve-then-expand options) change nothing about what is indexed, so a
    session that only changed them must not have its fitted retriever deleted.
    The reduction is recursive, so a composite's children and nested components
    are compared by their own signatures too.

    Parameters
    ----------
    reference : Any
        A ``{"component", "params"}`` retriever reference, or any other value.
    registry : ComponentRegistry | None
        Registry used to resolve the retriever classes.

    Returns
    -------
    Any
        The reference with ``params`` reduced to its persistence signature, or
        the value unchanged when it is not a retriever reference.

    Raises
    ------
    ValueError
        If *reference* is a retriever reference and no registry was given.
    """
    canonical = normalize_payload(reference)
    if not is_component_ref(canonical):
        return canonical
    if registry is None:
        raise ValueError(
            "CleanupService needs a component registry to compare retriever "
            "configurations."
        )
    return reference_signature(canonical, registry)


def _stored_reference(parameters: dict[str, Any], key: str) -> dict[str, Any]:
    """Return the stored component reference under ``key``, or ``{}`` for none.

    A session that never set the parameter, or stored it as null, has no
    reference to clean up, so ``{}`` says so. Any other value must be an object,
    since a reference is always a ``{component, params}`` mapping.

    Parameters
    ----------
    parameters : dict[str, Any]
        Session parameters, possibly without ``key``.
    key : str
        The parameter whose reference is read, such as ``retriever_model``.

    Returns
    -------
    dict[str, Any]
        The stored reference, or ``{}`` when the parameter is absent or null.

    Raises
    ------
    ValueError
        If the stored value is neither null nor an object.
    """
    reference = parameters.get(key)
    if reference is None:
        return {}
    if not isinstance(reference, dict):
        raise ValueError(
            f"Stored parameter {key!r} must be a component reference object."
        )
    return reference


def _retriever_component_name(parameters: dict[str, Any]) -> str | None:
    """Return the class name of the retriever a session's parameters name.

    Parameters
    ----------
    parameters : dict[str, Any]
        Session parameters, possibly without a retriever.

    Returns
    -------
    str | None
        The ``component`` of the retriever reference, or ``None`` when the
        session names no retriever or the reference has no component. A
        reference that exists but has no component is logged as a warning, since
        nothing can be matched for it.
    """
    retriever_model = _stored_reference(parameters, RAG_PARAM_RETRIEVER_MODEL)
    component = retriever_model.get(COMPONENT_KEY)
    if retriever_model and not component:
        log.warning(
            "The retriever reference of a session has no component; no retriever "
            "bridge is matched for it."
        )
    return component


def _folder_key(path: str) -> str:
    """Return the key under which two spellings of one folder compare equal.

    The key uses the same normalisation as :func:`_is_within`, so a folder
    reached through a junction or symlink keys the same as its target.

    Parameters
    ----------
    path : str
        A folder path as stored on a retriever or matrix row.

    Returns
    -------
    str
        The resolved path, with the case and separators the platform uses.
    """
    return os.path.normcase(os.path.realpath(path))


def _is_within(path: str | Path, root: str | Path) -> bool:
    """Whether a path lies strictly inside a folder, after resolving links.

    Parameters
    ----------
    path : str | Path
        The candidate. It need not exist.
    root : str | Path
        The folder it must lie under.

    Returns
    -------
    bool
        ``True`` when the resolved path is a proper descendant of the resolved
        root. A path on another drive is never inside.
    """
    candidate = os.path.normcase(os.path.realpath(path))
    base = os.path.normcase(os.path.realpath(root))
    if candidate == base:
        return False
    try:
        return os.path.commonpath([candidate, base]) == base
    except ValueError:
        return False


def _storage_roots(rag_path: str | Path) -> list[Path]:
    """Return the storage folders a post-index removal must stay inside.

    Parameters
    ----------
    rag_path : str | Path
        The ``RAG_PATH`` setting.

    Returns
    -------
    list[Path]
        ``<rag_path>/sparse_retrievers``, ``<rag_path>/embeddings`` and
        ``<rag_path>/chunk_sets``.
    """
    root = Path(rag_path)
    return [
        root / SPARSE_RETRIEVERS_DIRNAME,
        root / EMBEDDINGS_DIRNAME,
        root / CHUNK_SETS_DIRNAME,
    ]


def _is_within_any(path: str, roots: list[Path]) -> bool:
    """Whether a path lies inside at least one of the given folders.

    Parameters
    ----------
    path : str
        The candidate path.
    roots : list[Path]
        The folders to test against.

    Returns
    -------
    bool
    """
    return any(_is_within(path, root) for root in roots)


class CleanupService:
    """Cascade deletion of RAG resources when a session is deleted or updated.

    Responsible for removing orphaned retriever models, chunking models,
    embedding matrices, and storage folders when a generative session is
    deleted or its parameters are updated. Order of operations is critical:
    retrievers must be cleaned up BEFORE chunking models.

    The post-index cleanup (:meth:`cleanup_after_reindex`) is scoped to one
    session, and only its candidates come from that session's stale rows. Two
    known limitations remain, and no global lock is taken to close them:

    - Embedding models are keyed by configuration, not by session. A model that
      another session's in-flight index has resolved but not yet referenced
      could be released here. That needs more than one concurrent consumer; the
      Huey consumer currently runs a single worker.
    - The same applies to a chat turn and an index job of the same session,
      which can run concurrently.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    registry : ComponentRegistry | None
        Registry used to compare retriever configurations when a session's
        parameters are updated. Not needed for deletion-only use.
    rag_path : str | Path | None
        The RAG storage root (``RAG_PATH``). Required by
        :meth:`cleanup_after_reindex`, which only removes folders inside it.
        When omitted, the other cascade paths remove folders as they always
        have.
    """

    def __init__(
        self,
        db: Session,
        registry: ComponentRegistry | None = None,
        *,
        rag_path: str | Path | None = None,
    ):
        """Bind the cleanup to a session, and optionally a registry and storage root.

        Parameters
        ----------
        db : Session
            SQLAlchemy session the cleanup reads and writes in. Methods that take
            a ``commit`` flag leave the commit to the caller when it is ``False``.
        registry : ComponentRegistry | None, optional
            Registry used to compare retriever configurations when a session's
            parameters are updated. Not needed for deletion-only use.
        rag_path : str | Path | None, optional
            The RAG storage root (``RAG_PATH``). Required by
            :meth:`cleanup_after_reindex`, which only removes folders inside it.
            When omitted, the other cascade paths remove folders as they always
            have.
        """
        self.db = db
        self._registry = registry
        self._rag_path = rag_path
        self._retriever_db = RetrieverDBService(db)

    def cleanup_orphaned_resources(
        self,
        session_id: int,
        old_parameters: dict[str, Any],
        new_parameters: dict[str, Any] | None = None,
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
                """Whether one parameter of the session really changed.

                Parameters
                ----------
                key : str
                    Session parameter name, such as ``retriever_model``.

                Returns
                -------
                bool
                    ``True`` on full session deletion, when the raw value differs
                    for a non-retriever parameter, or when a retriever's identity
                    differs. Identical raw values are never a change.
                """
                if new_parameters is None:
                    return True
                old_value = old_parameters.get(key)
                new_value = new_parameters.get(key)
                # Identical raw values cannot differ in identity, so the registry
                # is only needed when the configuration really changed.
                if configs_equal(old_value, new_value):
                    return False
                if key != RAG_PARAM_RETRIEVER_MODEL:
                    return True
                return self._retriever_changed(old_value, new_value)

            # ── Retriever cleanup (MUST run BEFORE chunking) ──
            retriever_model_params = _stored_reference(
                old_parameters, RAG_PARAM_RETRIEVER_MODEL
            )

            # The retriever rows deleted below hang off this session's chunk
            # set, which no other session can share now that documents belong
            # to one session. Rows keyed by configuration alone -- the chunking
            # model here, the embedding model in _release_dense_storage -- *are*
            # shared, and are guarded where they are deleted.
            should_cleanup_retriever = bool(retriever_model_params) and (
                _component_changed(RAG_PARAM_RETRIEVER_MODEL)
            )

            if should_cleanup_retriever:
                self._cleanup_retriever(old_parameters, session_id)

            # ── Chunking model cleanup (AFTER retriever) ──
            chunking_model_params = _stored_reference(
                old_parameters, RAG_PARAM_CHUNKING_MODEL
            )

            should_cleanup_chunking = bool(chunking_model_params) and (
                _component_changed(RAG_PARAM_CHUNKING_MODEL)
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

    def _retriever_changed(self, old_value: Any, new_value: Any) -> bool:
        """Whether a retriever reference changed in a way that affects its fit.

        An old reference whose component is no longer registered, typically
        because its plugin was uninstalled, cannot be reduced to a signature and
        so cannot be shown to match the new one. It is taken as changed, which
        lets the session move off it; the orphaned fitted state is then released.

        Parameters
        ----------
        old_value : Any
            The retriever reference before the update.
        new_value : Any
            The retriever reference after the update.

        Returns
        -------
        bool
            ``True`` when the identities differ, or when the old reference's
            component cannot be resolved.

        Raises
        ------
        ValueError
            If a retriever reference must be compared and no registry was given.
        """
        try:
            old_identity = _retriever_identity(old_value, self._registry)
        except RAGComponentNotFoundError as error:
            log.warning("%s; treating the retriever as changed.", error)
            return True
        new_identity = _retriever_identity(new_value, self._registry)
        return not configs_equal(old_identity, new_identity)

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

    def _folder_in_use(
        self,
        model: type[RAGSparseRetriever] | type[RAGEmbeddingMatrix],
        storage_folder: str,
        exclude_ids: Sequence[int],
    ) -> bool:
        """Whether a row of ``model`` outside ``exclude_ids`` reaches a folder.

        Rows are compared by their normalised folder key, so the same folder
        spelled with forward slashes, a trailing separator or another drive-letter
        case still counts as in use. The tables hold one row per fitted index or
        matrix, so every row is read and compared in Python.

        Parameters
        ----------
        model : type
            The row class whose ``storage_folder`` is compared.
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
        key = _folder_key(storage_folder)
        excluded = set(exclude_ids)
        for row_id, folder in self.db.query(model.id, model.storage_folder).all():
            if row_id in excluded:
                continue
            if _folder_key(folder) == key:
                return True
        return False

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
        return self._folder_in_use(RAGSparseRetriever, storage_folder, exclude_ids)

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
        return self._folder_in_use(RAGEmbeddingMatrix, storage_folder, exclude_ids)

    def _queue_removal(self, path: str | None) -> None:
        """Queue a storage folder for removal once the transaction commits.

        Every removal of the post-index path goes through here. When a RAG root
        was given, the folder must lie inside one of the storage sub-folders, so
        a row that points elsewhere cannot delete unrelated files. The caller
        still deletes the row; only the folder is kept. Without a root, removal
        is queued as it always was.

        Accepted trade-off: when ``RAG_PATH`` changed after indexing, the stored
        rows point outside the current root. Their folders are then kept with a
        warning while the rows are deleted, so the folders are never retried by
        a later cleanup and must be removed by hand if wanted.

        Parameters
        ----------
        path : str | None
            The folder to remove. ``None`` is ignored, as by
            :func:`remove_after_commit`.
        """
        if (
            self._rag_path is not None
            and path
            and not _is_within_any(path, _storage_roots(self._rag_path))
        ):
            log.warning(
                "Not removing %s: it is outside the RAG storage folders. Its rows "
                "are deleted and the folder is kept.",
                path,
            )
            return
        remove_after_commit(self.db, path)

    def _queue_chunk_set_removal(self, chunk_set_id: int) -> None:
        """Queue the chunk folders of one chunk set for removal.

        Without a RAG root, the parent of each stored document folder is queued,
        as it always was. With one, only the chunk set's own folder
        ``<rag_path>/chunk_sets/<chunk_set_id>`` can go, and only when a stored
        folder lies inside it. Any other stored path is kept and logged.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set being invalidated. Its rows are still present.
        """
        rows = (
            self.db.query(RAGChunkSetDocument.path)
            .filter(
                RAGChunkSetDocument.chunk_set_id == chunk_set_id,
                RAGChunkSetDocument.path.isnot(None),
            )
            .all()
        )
        paths: list[str] = []
        for row in rows:
            paths.append(row[0])
        if self._rag_path is None:
            parent_folders: set[str] = set()
            for path in paths:
                parent_folders.add(str(Path(path).parent))
            for folder in parent_folders:
                remove_after_commit(self.db, folder)
            return
        chunk_set_dir = str(
            Path(self._rag_path) / CHUNK_SETS_DIRNAME / str(chunk_set_id)
        )
        owned = False
        for path in paths:
            if _is_within(path, chunk_set_dir):
                owned = True
                continue
            log.warning(
                "Not removing chunk folder %s: it is outside chunk set %d's folder. "
                "Its rows are deleted and the folder is kept.",
                path,
                chunk_set_id,
            )
        if owned:
            self._queue_removal(chunk_set_dir)
        else:
            log.warning(
                "Not removing chunk set %d's folder %s: no stored chunk path lies "
                "inside it. Its rows are deleted and the folder is kept.",
                chunk_set_id,
                chunk_set_dir,
            )

    def _embedding_model_in_use(self, embedding_model_id: int) -> bool:
        """Whether anything still references an embedding model.

        Parameters
        ----------
        embedding_model_id : int

        Returns
        -------
        bool
        """
        retrievers = self.db.query(RAGDenseRetriever).filter(
            RAGDenseRetriever.embedding_model_id == embedding_model_id
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

    def _cleanup_retriever(
        self, old_parameters: dict[str, Any], session_id: int
    ) -> None:
        """Release the retriever bridges that a session's parameter update replaces.

        Every bridge of the retriever class the session named, in its pipeline, is
        released, whether it is a composite or a unit. A composite is torn down
        top-down with the children that no surviving tree still reads. A unit's
        sparse folder goes once no other row uses it, and its dense matrices and
        model go once nothing reads them. A unit bridge that a surviving composite
        still reads is kept, with that composite. The other pipeline roots are
        kept too. The matrices and models of the dense leaves that were deleted
        are released by :meth:`_release_dense_storage`.

        Parameters
        ----------
        old_parameters : dict[str, Any]
            Session parameters before the update, holding the old retriever.
        session_id : int
            Generative session identifier.
        """
        class_name = _retriever_component_name(old_parameters)
        if class_name is None:
            # The session names no retriever class, so there is nothing to
            # release. Querying with no class would match only rows that have
            # no class name at all, which is never what a session means.
            return
        self._release_class_bridges(session_id, class_name)

    def _release_class_bridges(self, session_id: int, class_name: str) -> None:
        """Release every bridge of one class in a session's pipeline.

        Parameters
        ----------
        session_id : int
            Generative session identifier.
        class_name : str
            The class whose bridges are released, composite or unit.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            return
        # Every bridge of the class in this pipeline belongs to the configuration
        # being replaced, so all of them go, not only the first one found. Other
        # roots are kept, and so is every bridge a surviving tree still reads.
        bridge_ids = self._bridge_ids_of_class(pipeline_id, class_name)
        release = self._release_bridge_trees(
            bridge_ids,
            self._other_roots(pipeline_id, bridge_ids),
            frozenset(),
        )
        self._release_dense_storage(release)

    def _bridge_ids_of_class(self, pipeline_id: int, class_name: str) -> list[int]:
        """List the bridge ids of one class in a pipeline, in ascending order.

        Parameters
        ----------
        pipeline_id : int
            The pipeline whose bridges are listed.
        class_name : str
            The retriever class to match.

        Returns
        -------
        list[int]
            The matching bridge ids, ascending.
        """
        rows = (
            self.db.query(RAGRetriever.id)
            .filter(
                RAGRetriever.pipeline_id == pipeline_id,
                RAGRetriever.class_name == class_name,
            )
            .order_by(RAGRetriever.id)
            .all()
        )
        return [row[0] for row in rows]

    def _release_dense_storage(self, release: _BridgeRelease) -> None:
        """Release the matrices and embedding models that deleted dense leaves used.

        A chunk set and model pair that no surviving dense leaf reads loses its
        matrices, and each matrix folder goes once no other row uses it. Then
        every model the release touched is deleted, unless a row still references
        it. A pair that a surviving leaf still reads is left alone.

        Parameters
        ----------
        release : _BridgeRelease
            The release whose dense leaves were deleted.
        """
        self.db.flush()
        model_ids = set(release.model_ids)
        for chunk_set_id, model_id in sorted(release.dense_leaves):
            if self._pair_still_read(chunk_set_id, model_id):
                continue
            matrices = (
                self.db.query(RAGEmbeddingMatrix)
                .filter(
                    RAGEmbeddingMatrix.chunk_set_id == chunk_set_id,
                    RAGEmbeddingMatrix.embedding_model_id == model_id,
                )
                .all()
            )
            model_ids |= self._drop_matrices(matrices)
        self.db.flush()
        self._release_unused_models(model_ids)

    def _pair_still_read(self, chunk_set_id: int, embedding_model_id: int) -> bool:
        """Whether a surviving dense leaf reads a chunk set with an embedding model.

        Parameters
        ----------
        chunk_set_id : int
        embedding_model_id : int

        Returns
        -------
        bool
        """
        readers = (
            self.db.query(RAGDenseRetriever)
            .filter(
                RAGDenseRetriever.chunk_set_id == chunk_set_id,
                RAGDenseRetriever.embedding_model_id == embedding_model_id,
            )
            .count()
        )
        return readers > 0

    def _delete_bridge_row(self, bridge: RAGRetriever) -> None:
        """Delete a bridge row and every child link that points at it.

        The links where the bridge is the parent are removed with it through
        the ORM cascade. The links where it is a child are removed explicitly,
        because nothing else would remove them and they would dangle.

        Every deletion of a bridge goes through here, the composites and the
        leaves of :meth:`_release_bridge_trees` alike.

        Parameters
        ----------
        bridge : RAGRetriever
            The bridge row to delete.
        """
        self.db.query(RAGRetrieverChild).filter(
            RAGRetrieverChild.child_id == bridge.id
        ).delete(synchronize_session="fetch")
        self.db.delete(bridge)

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
        rows = self.db.query(RAGChunkSet.id).filter(
            RAGChunkSet.session_id == session_id
        )
        chunk_set_ids: list[int] = []
        for row in rows:
            chunk_set_ids.append(row[0])
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
        rows = self.db.query(RAGChunkSet.id).filter(RAGChunkSet.session_id.is_(None))
        chunk_set_ids: list[int] = []
        for row in rows.all():
            chunk_set_ids.append(row[0])
        for chunk_set_id in chunk_set_ids:
            self._invalidate_chunk_set(chunk_set_id)
        if commit:
            self.db.commit()
        return len(chunk_set_ids)

    def _invalidate_chunk_set(self, chunk_set_id: int) -> None:
        """Delete one chunk set and everything fitted on it.

        Removes the composite retrievers built over its retrievers, its sparse
        and dense retrievers, every embedding matrix that carries its id (linked
        to a dense retriever or not), the embedding models that nothing else
        uses, and the chunk set itself, whose chunks and membership rows go with
        it. Chunk folders belong to one chunk set, so they are queued for removal
        with it; see :meth:`_queue_chunk_set_removal`.

        The retrievers fitted on the chunk set are the doomed leaves. Every
        pipeline tree that reaches one of them is torn down top-down, and the
        trees that do not are kept, so a composite of another chunk set that
        still stands is left alone. A leaf that no root reaches, for example one
        behind a rootless cycle, is deleted directly, so that no leaf is left
        pointing at the chunk set. See :meth:`_release_bridge_trees` for the
        deletion order.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set to delete.
        """
        doomed = self._chunk_set_bridge_ids(chunk_set_id)
        release = self._release_chunk_set_trees(doomed)
        model_ids = set(release.model_ids)
        model_ids |= self._drop_leftover_leaves(chunk_set_id)
        model_ids |= self._drop_chunk_set_matrices(chunk_set_id)
        self.db.flush()
        self._release_unused_models(model_ids)
        self._queue_chunk_set_removal(chunk_set_id)
        chunk_set = self.db.get(RAGChunkSet, chunk_set_id)
        if chunk_set is not None:
            self.db.delete(chunk_set)

    def _drop_leftover_leaves(self, chunk_set_id: int) -> set[int]:
        """Delete the leaves of a chunk set that the pipeline trees did not release.

        Runs after :meth:`_release_chunk_set_trees`. A leaf that is still listed
        sits behind no root, so nothing else would delete it and it would keep
        pointing at the chunk set. A listed bridge that has lost its fitted
        detail is deleted outright, since no tree would reach it. Composites
        belong to the trees that hold them and are not touched here.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set being invalidated.

        Returns
        -------
        set[int]
            Embedding models the deleted dense leaves used.
        """
        leftover = sorted(self._chunk_set_bridge_ids(chunk_set_id))
        if not leftover:
            return set()
        leaves: list[RAGRetriever] = []
        for bridge_id in leftover:
            bridge = self.db.get(RAGRetriever, bridge_id)
            if bridge is None:
                # Already gone, so there is no row left to delete.
                continue
            if bridge.sparse_detail is None and bridge.dense_detail is None:
                self._delete_bridge_row(bridge)
            else:
                leaves.append(bridge)
        return _model_ids_of(self._drop_leaf_bridges(leaves))

    def _chunk_set_bridge_ids(self, chunk_set_id: int) -> frozenset[int]:
        """List the bridges of the sparse and dense leaves fitted on a chunk set.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set whose fitted leaves are listed.

        Returns
        -------
        frozenset[int]
            Bridge ids of the leaves that read the chunk set.
        """
        bridge_ids: set[int] = set()
        sparse_rows = (
            self.db.query(RAGSparseRetriever.bridge_id)
            .filter(RAGSparseRetriever.chunk_set_id == chunk_set_id)
            .all()
        )
        for row in sparse_rows:
            bridge_ids.add(row[0])
        dense_rows = (
            self.db.query(RAGDenseRetriever.bridge_id)
            .filter(RAGDenseRetriever.chunk_set_id == chunk_set_id)
            .all()
        )
        for row in dense_rows:
            bridge_ids.add(row[0])
        return frozenset(bridge_ids)

    def _release_chunk_set_trees(self, doomed: frozenset[int]) -> _BridgeRelease:
        """Release the pipeline trees that hold doomed leaves.

        The pipelines are those of the doomed bridges. In each one, a root whose
        tree reaches a doomed leaf is torn down; every other root is kept, with
        the trees under it. A chunk set without a bridge in any pipeline releases
        nothing here, and its rows are deleted by the caller.

        Parameters
        ----------
        doomed : frozenset[int]
            Bridge ids of the leaves that read the chunk set being invalidated.

        Returns
        -------
        _BridgeRelease
            Bridges deleted, and the embedding models their dense details used.
        """
        roots: list[int] = []
        keep: list[int] = []
        for pipeline_id in self._pipelines_of(doomed):
            for root_id in self._pipeline_root_ids(pipeline_id):
                if self._reaches(root_id, doomed):
                    roots.append(root_id)
                else:
                    keep.append(root_id)
        return self._release_bridge_trees(roots, keep, doomed)

    def _pipelines_of(self, bridge_ids: frozenset[int]) -> set[int]:
        """List the pipelines that own the given bridges.

        Parameters
        ----------
        bridge_ids : frozenset[int]
            Bridges whose owning pipelines are wanted. Ids of bridges that no
            longer exist contribute nothing.

        Returns
        -------
        set[int]
            Pipeline ids of the bridges that still exist.
        """
        pipeline_ids: set[int] = set()
        for bridge_id in bridge_ids:
            bridge = self.db.get(RAGRetriever, bridge_id)
            if bridge is not None:
                pipeline_ids.add(bridge.pipeline_id)
        return pipeline_ids

    def _tree_order(self, root_ids: Sequence[int]) -> list[int]:
        """List every bridge under the given roots, parents before children.

        The walk keeps an explicit stack, so a composite nested at any depth is
        reached without recursion. Children are pushed in reverse, so they pop
        in ``child_order``, which makes the result a pre-order walk. A bridge
        reached more than once, through a shared child or a cycle, is listed
        only at its first visit.

        Parameters
        ----------
        root_ids : Sequence[int]
            The roots to walk from. Each one is listed before its children.

        Returns
        -------
        list[int]
            The de-duplicated bridge ids, top-down.
        """
        order: list[int] = []
        seen: set[int] = set()
        pending = list(reversed(root_ids))
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            order.append(current)
            pending.extend(reversed(self._retriever_db.child_ids_in_order(current)))
        return order

    def _reaches(self, root_id: int, bridge_ids: frozenset[int]) -> bool:
        """Whether the tree under a root contains any of the given bridges.

        Parameters
        ----------
        root_id : int
            The root whose tree is searched.
        bridge_ids : frozenset[int]
            The bridges to look for.

        Returns
        -------
        bool
        """
        return any(bridge_id in bridge_ids for bridge_id in self._tree_order([root_id]))

    def _pipeline_root_ids(self, pipeline_id: int) -> list[int]:
        """List the bridges of a pipeline that no child link points at.

        Each root heads one tree. A link can name a bridge of another pipeline
        only through corrupt data, so the referenced set is read whole.

        Parameters
        ----------
        pipeline_id : int
            The pipeline whose roots are listed.

        Returns
        -------
        list[int]
            Root bridge ids in ascending order.
        """
        referenced: set[int] = set()
        for row in self.db.query(RAGRetrieverChild.child_id).all():
            referenced.add(row[0])
        bridge_rows = (
            self.db.query(RAGRetriever.id)
            .filter(RAGRetriever.pipeline_id == pipeline_id)
            .order_by(RAGRetriever.id)
            .all()
        )
        roots: list[int] = []
        for row in bridge_rows:
            if row[0] not in referenced:
                roots.append(row[0])
        return roots

    def _other_roots(self, pipeline_id: int, excluded: Sequence[int]) -> list[int]:
        """List the pipeline's roots that are not in ``excluded``.

        Parameters
        ----------
        pipeline_id : int
            The pipeline whose roots are listed.
        excluded : Sequence[int]
            Roots being torn down, or the live root, which is not a candidate.

        Returns
        -------
        list[int]
            The remaining root bridge ids, in ascending order.
        """
        skipped = set(excluded)
        remaining: list[int] = []
        for root_id in self._pipeline_root_ids(pipeline_id):
            if root_id not in skipped:
                remaining.append(root_id)
        return remaining

    def _release_bridge_trees(
        self,
        roots: Sequence[int],
        keep_roots: Sequence[int],
        doomed_leaves: frozenset[int],
    ) -> _BridgeRelease:
        """Delete the trees under ``roots``, except what ``keep_roots`` reaches.

        Every bridge under ``roots`` is deleted unless a tree under
        ``keep_roots`` still references it, directly or through children. A
        child is therefore removed only when no surviving tree references it.
        The leaves in ``doomed_leaves`` are deleted even when a kept tree reaches
        them, and every deleted bridge takes its child links with it.

        Deletion order is fixed, and each step goes through
        :meth:`_delete_bridge_row`:

        1. composites, and bridges without a fitted detail, top-down;
        2. leaves, each one's fitted details first (a sparse folder is queued only
           once no other row uses it; a dense row is deleted), then its bridge;
        3. the embedding matrices and models are not touched here. The
           ``(chunk set, model)`` pairs of the dense leaves are returned instead.

        Contract: this method deletes bridges, child links and fitted details
        only. The caller must release the matrices and models of the returned
        dense leaves, through :meth:`_release_dense_storage` or, for the
        post-index path, :meth:`_release_unused_matrices`. Otherwise those rows
        are left orphaned.

        Parameters
        ----------
        roots : Sequence[int]
            Roots whose trees are torn down.
        keep_roots : Sequence[int]
            Roots whose trees survive.
        doomed_leaves : frozenset[int]
            Leaf bridges deleted even when a surviving tree reaches them.

        Returns
        -------
        _BridgeRelease
            Bridges deleted, and the ``(chunk set, model)`` pairs of the dense
            leaves deleted.
        """
        surviving = set(self._tree_order(keep_roots)) - doomed_leaves
        deleting: list[int] = []
        for bridge_id in self._tree_order(roots):
            if bridge_id not in surviving:
                deleting.append(bridge_id)
        composites, leaves = self._partition_bridges(deleting)
        for bridge in composites:
            self._delete_bridge_row(bridge)
        dense_leaves = self._drop_leaf_bridges(leaves)
        self.db.flush()
        return _BridgeRelease(
            bridges=len(composites) + len(leaves),
            dense_leaves=frozenset(dense_leaves),
        )

    def _partition_bridges(
        self, bridge_ids: list[int]
    ) -> tuple[list[RAGRetriever], list[RAGRetriever]]:
        """Split bridges into composites and leaves, keeping their order.

        A leaf is a bridge with a fitted detail. Every other bridge, including
        one with neither a detail nor children, counts as a composite.

        Parameters
        ----------
        bridge_ids : list[int]
            Bridge ids to split. Ids of bridges that no longer exist are skipped.

        Returns
        -------
        tuple[list[RAGRetriever], list[RAGRetriever]]
            The composites and the leaves.
        """
        composites: list[RAGRetriever] = []
        leaves: list[RAGRetriever] = []
        for bridge_id in bridge_ids:
            bridge = self.db.get(RAGRetriever, bridge_id)
            if bridge is None:
                continue
            if bridge.sparse_detail is None and bridge.dense_detail is None:
                composites.append(bridge)
            else:
                leaves.append(bridge)
        return composites, leaves

    def _drop_leaf_bridges(self, leaves: list[RAGRetriever]) -> set[tuple[int, int]]:
        """Delete leaf bridges together with every fitted detail they hold.

        A bridge may hold a sparse detail, a dense detail, or both, and every
        detail present is deleted. The bridge row goes last, once.

        Parameters
        ----------
        leaves : list[RAGRetriever]
            Bridges that each have a sparse or a dense detail.

        Returns
        -------
        set[tuple[int, int]]
            ``(chunk set id, embedding model id)`` of each dense detail deleted.
            The caller decides which matrices and models are still referenced.
        """
        sparse_details: list[RAGSparseRetriever] = []
        dense_details: list[RAGDenseRetriever] = []
        for bridge in leaves:
            if bridge.sparse_detail is not None:
                sparse_details.append(bridge.sparse_detail)
            if bridge.dense_detail is not None:
                dense_details.append(bridge.dense_detail)
        sparse_ids = [detail.id for detail in sparse_details]
        for sparse_detail in sparse_details:
            self._drop_sparse_detail(sparse_detail, sparse_ids)
        dense_pairs: set[tuple[int, int]] = set()
        for dense_detail in dense_details:
            dense_pairs.add(
                (dense_detail.chunk_set_id, dense_detail.embedding_model_id)
            )
            self.db.delete(dense_detail)
        for bridge in leaves:
            self._delete_bridge_row(bridge)
        return dense_pairs

    def _drop_chunk_set_matrices(self, chunk_set_id: int) -> set[int]:
        """Delete every embedding matrix of a chunk set, linked or not.

        A matrix can exist without a dense retriever that reads it, for example
        after a failed index. Matching on the chunk set itself catches those too,
        so the chunk set row can always be deleted.

        Parameters
        ----------
        chunk_set_id : int
            The chunk set whose matrices go.

        Returns
        -------
        set[int]
            Embedding models the deleted matrices used.
        """
        matrices = (
            self.db.query(RAGEmbeddingMatrix)
            .filter(RAGEmbeddingMatrix.chunk_set_id == chunk_set_id)
            .all()
        )
        return self._drop_matrices(matrices)

    def _drop_matrices(self, matrices: list[RAGEmbeddingMatrix]) -> set[int]:
        """Delete embedding matrix rows, and each folder once nothing else uses it.

        Parameters
        ----------
        matrices : list[RAGEmbeddingMatrix]
            The rows to delete. Rows in this list do not count as live references
            to each other's folders.

        Returns
        -------
        set[int]
            Embedding models the deleted matrices used.
        """
        doomed_ids = [matrix.id for matrix in matrices]
        model_ids: set[int] = set()
        for matrix in matrices:
            model_ids.add(matrix.embedding_model_id)
            if not self._embedding_folder_in_use(
                matrix.storage_folder, exclude_ids=doomed_ids
            ):
                self._queue_removal(matrix.storage_folder)
            self.db.delete(matrix)
        return model_ids

    def cleanup_after_reindex(
        self, session_id: int, live_root_bridge_id: int
    ) -> IndexCleanupSummary:
        """Release what a session's reindex left behind, in one transaction.

        The live index is the tree under ``live_root_bridge_id``: the root and
        every bridge reached through the child links. Its leaves fix the live
        chunk set, which must belong to the session. Anything else of the
        session is an orphan:

        1. chunk sets of the session other than the live one, with their
           retrievers, matrices and chunk folders;
        2. pipeline bridges outside the live tree: stale composites with their
           child links, and stale unit retrievers with their sparse or dense
           detail;
        3. embedding matrices of the live chunk set that no live dense
           retriever uses, and the embedding models this leaves unused.

        Scope is the session, never the database or the disk. Candidates come
        only from this session's stale rows, so a distinct-configuration model
        of another session is never a candidate, and nothing unreferenced on
        disk is swept. Embedding models are keyed by configuration, though, so
        a model that another session's in-flight index has resolved but not yet
        referenced could be released here. That needs more than one concurrent
        consumer, and the same holds for a chat turn and an index job of the
        same session. Both are known limitations; no global lock is taken.

        A shared folder or model is removed only once no surviving row uses it,
        and every folder removed lies inside the RAG storage root.

        Calling it again when nothing is stale changes nothing.

        Parameters
        ----------
        session_id : int
            The session that was just indexed.
        live_root_bridge_id : int
            Bridge id of the root of the retriever the reindex built.

        Returns
        -------
        IndexCleanupSummary
            How many rows of each kind were released.

        Raises
        ------
        ValueError
            If no RAG storage root was given to the service, the session has no
            pipeline, the root is unknown or belongs to another pipeline, or the
            live retrievers do not read exactly one chunk set owned by the
            session. Nothing is deleted in that case.
        """
        if self._rag_path is None:
            raise ValueError(
                "cleanup_after_reindex needs the RAG storage root to check the "
                "folders it removes; construct CleanupService with rag_path."
            )
        try:
            live = self._live_index(session_id, live_root_bridge_id)
            chunk_sets = self._invalidate_stale_chunk_sets(
                session_id, live.chunk_set_id
            )
            bridges = self._release_stale_bridges(live)
            matrices = self._release_unused_matrices(live, bridges.model_ids)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return IndexCleanupSummary(
            chunk_sets=chunk_sets,
            bridges=bridges.bridges,
            embedding_matrices=matrices.matrices,
            embedding_models=matrices.models,
        )

    def _live_index(self, session_id: int, root_id: int) -> _LiveIndex:
        """Resolve and validate the live index rooted at ``root_id``.

        Parameters
        ----------
        session_id : int
            The generative session that owns the index.
        root_id : int
            The root bridge of the index. It must belong to the session's
            pipeline.

        Returns
        -------
        _LiveIndex

        Raises
        ------
        ValueError
            If the session has no pipeline, or the root is unknown or belongs
            to another pipeline.
        """
        pipeline_id = self._find_pipeline_id(session_id)
        if pipeline_id is None:
            raise ValueError(f"Session {session_id} has no pipeline to clean up.")
        root = self.db.get(RAGRetriever, root_id)
        if root is None or root.pipeline_id != pipeline_id:
            raise ValueError(
                f"Retriever {root_id} is not a retriever of session {session_id}."
            )
        bridge_ids = set(self._tree_order([root_id]))
        self._assert_same_pipeline(session_id, bridge_ids, pipeline_id)
        leaves = self._live_leaves(session_id, bridge_ids)
        return _LiveIndex(
            pipeline_id=pipeline_id,
            root_id=root_id,
            chunk_set_id=leaves.chunk_set_id,
            dense_model_ids=leaves.dense_model_ids,
        )

    def _assert_same_pipeline(
        self, session_id: int, bridge_ids: set[int], pipeline_id: int
    ) -> None:
        """Refuse a live tree that reaches a bridge of another pipeline.

        Parameters
        ----------
        session_id : int
        bridge_ids : set[int]
            The bridges of the live tree.
        pipeline_id : int
            The session's own pipeline.

        Raises
        ------
        ValueError
            If a bridge of the tree belongs to another pipeline.
        """
        for bridge_id in bridge_ids:
            bridge = self.db.get(RAGRetriever, bridge_id)
            if bridge is not None and bridge.pipeline_id != pipeline_id:
                raise ValueError(
                    f"The retriever tree of session {session_id} reaches another "
                    "session's pipeline."
                )

    def _live_leaves(self, session_id: int, bridge_ids: set[int]) -> _LiveLeaves:
        """Validate the leaves of a live tree and read its chunk set and models.

        Every bridge must be either a leaf with a fitted detail or a composite
        with children. The leaves must all read one chunk set, owned by the
        session.

        Parameters
        ----------
        session_id : int
        bridge_ids : set[int]
            The bridges of the live tree.

        Returns
        -------
        _LiveLeaves
            The live chunk set id and the embedding models of the dense leaves.

        Raises
        ------
        ValueError
            If a bridge is neither a leaf nor a composite, or the leaves do not
            read exactly one chunk set owned by the session.
        """
        ids = list(bridge_ids)
        sparse = (
            self.db.query(RAGSparseRetriever)
            .filter(RAGSparseRetriever.bridge_id.in_(ids))
            .all()
        )
        dense = (
            self.db.query(RAGDenseRetriever)
            .filter(RAGDenseRetriever.bridge_id.in_(ids))
            .all()
        )
        leaves = sparse + dense
        leaf_ids = {detail.bridge_id for detail in leaves}
        composite_ids: set[int] = set()
        for bridge_id in bridge_ids:
            if self._retriever_db.child_ids_in_order(bridge_id):
                composite_ids.add(bridge_id)
        if bridge_ids - leaf_ids - composite_ids:
            raise ValueError(
                f"A retriever of session {session_id} has neither a fitted detail "
                "nor children."
            )
        chunk_set_id = self._owned_chunk_set(
            session_id, {detail.chunk_set_id for detail in leaves}
        )
        return _LiveLeaves(
            chunk_set_id=chunk_set_id,
            dense_model_ids=frozenset(detail.embedding_model_id for detail in dense),
        )

    def _owned_chunk_set(self, session_id: int, chunk_set_ids: set[int]) -> int:
        """Return the one chunk set the live retrievers read, if the session owns it.

        Parameters
        ----------
        session_id : int
        chunk_set_ids : set[int]
            The chunk sets read by the live leaves.

        Returns
        -------
        int
            The chunk set id.

        Raises
        ------
        ValueError
            If the leaves read other than exactly one chunk set, or that chunk
            set is not owned by the session.
        """
        if len(chunk_set_ids) != 1:
            raise ValueError(
                f"The live retriever of session {session_id} must read exactly one "
                f"chunk set, found {len(chunk_set_ids)}."
            )
        chunk_set_id = next(iter(chunk_set_ids))
        owner = self.db.get(RAGChunkSet, chunk_set_id)
        if owner is None or owner.session_id != session_id:
            raise ValueError(
                f"Chunk set {chunk_set_id} of the live retriever is not owned by "
                f"session {session_id}."
            )
        return chunk_set_id

    def _invalidate_stale_chunk_sets(
        self, session_id: int, live_chunk_set_id: int
    ) -> int:
        """Invalidate every chunk set of the session except the live one.

        Parameters
        ----------
        session_id : int
        live_chunk_set_id : int
            The chunk set the live retriever reads, which is kept.

        Returns
        -------
        int
            Number of chunk sets invalidated.
        """
        rows = self.db.query(RAGChunkSet.id).filter(
            RAGChunkSet.session_id == session_id,
            RAGChunkSet.id != live_chunk_set_id,
        )
        stale_ids: list[int] = []
        for row in rows.all():
            stale_ids.append(row[0])
        for chunk_set_id in stale_ids:
            self._invalidate_chunk_set(chunk_set_id)
        return len(stale_ids)

    def _release_stale_bridges(self, live: _LiveIndex) -> _BridgeRelease:
        """Release every pipeline tree other than the live one.

        The roots of the other trees are torn down top-down, so composites nested
        at any depth go with their children. The live root is kept, and with it
        every bridge the live tree reaches. A dense detail is deleted, but its
        embedding model is left to the caller to release.

        Parameters
        ----------
        live : _LiveIndex
            The validated live index, whose tree must survive.

        Returns
        -------
        _BridgeRelease
            The number of bridges released, and the embedding models their
            dense details used.
        """
        roots = self._other_roots(live.pipeline_id, [live.root_id])
        return self._release_bridge_trees(roots, [live.root_id], frozenset())

    def _drop_sparse_detail(
        self, detail: RAGSparseRetriever, stale_sparse_ids: Sequence[int]
    ) -> None:
        """Delete a stale sparse detail and its folder when nothing else uses it.

        Parameters
        ----------
        detail : RAGSparseRetriever
            The stale detail being deleted.
        stale_sparse_ids : Sequence[int]
            Every stale sparse detail, which must not count as a live reference.
        """
        if not self._sparse_folder_in_use(
            detail.storage_folder, exclude_ids=stale_sparse_ids
        ):
            self._queue_removal(detail.storage_folder)
        self.db.delete(detail)

    def _release_unused_matrices(
        self, live: _LiveIndex, candidate_models: frozenset[int]
    ) -> _MatrixRelease:
        """Release live-chunk-set matrices no live dense retriever needs.

        Parameters
        ----------
        live : _LiveIndex
            The validated live index.
        candidate_models : frozenset[int]
            Embedding models that the release may have left unused. The models
            of the matrices released here are added to them.

        Returns
        -------
        _MatrixRelease
            Matrices released, and embedding models deleted.
        """
        stale = self._stale_matrices(live)
        stale_ids = [matrix.id for matrix in stale]
        model_ids = set(candidate_models)
        for matrix in stale:
            model_ids.add(matrix.embedding_model_id)
            if not self._embedding_folder_in_use(
                matrix.storage_folder, exclude_ids=stale_ids
            ):
                self._queue_removal(matrix.storage_folder)
            self.db.delete(matrix)
        self.db.flush()
        return _MatrixRelease(
            matrices=len(stale), models=self._release_unused_models(model_ids)
        )

    def _stale_matrices(self, live: _LiveIndex) -> list[RAGEmbeddingMatrix]:
        """List the matrices of the live chunk set that no live dense retriever uses.

        Parameters
        ----------
        live : _LiveIndex
            The validated live index.

        Returns
        -------
        list[RAGEmbeddingMatrix]
        """
        stale: list[RAGEmbeddingMatrix] = []
        matrices = (
            self.db.query(RAGEmbeddingMatrix)
            .filter(RAGEmbeddingMatrix.chunk_set_id == live.chunk_set_id)
            .all()
        )
        for matrix in matrices:
            if matrix.embedding_model_id not in live.dense_model_ids:
                stale.append(matrix)
        return stale

    def _release_unused_models(self, model_ids: set[int]) -> int:
        """Delete each given embedding model that no row references any more.

        Parameters
        ----------
        model_ids : set[int]
            Candidate embedding model ids.

        Returns
        -------
        int
            Number of embedding models deleted.
        """
        removed = 0
        for model_id in sorted(model_ids):
            if self._embedding_model_in_use(model_id):
                continue
            model = self.db.get(RAGEmbeddingModel, model_id)
            if model is not None:
                self.db.delete(model)
                removed += 1
        self.db.flush()
        return removed


@dataclass(frozen=True)
class IndexFootprint:
    """The chunk sets and retriever bridges a session holds at one moment.

    Attributes
    ----------
    chunk_set_ids : frozenset[int]
        Chunk sets owned by the session.
    bridge_ids : frozenset[int]
        Retriever bridges of the session's pipeline, composites and leaves alike.
    """

    chunk_set_ids: frozenset[int]
    bridge_ids: frozenset[int]


def capture_index_footprint(db: Session, session_id: int) -> IndexFootprint:
    """Record which chunk sets and bridges a session holds right now.

    A build adds chunk sets and bridges and a cleanup removes them, so two
    footprints taken around a build differ exactly when the build created
    something new. A build that reuses every row leaves the footprint equal.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    session_id : int
        The generative session whose rows are counted.

    Returns
    -------
    IndexFootprint
        The session's chunk set ids and its pipeline's bridge ids.
    """
    chunk_set_rows = (
        db.query(RAGChunkSet.id).filter(RAGChunkSet.session_id == session_id).all()
    )
    chunk_set_ids: set[int] = set()
    for row in chunk_set_rows:
        chunk_set_ids.add(row[0])
    bridge_ids: set[int] = set()
    pipeline_row = db.query(RAGPipeline.id).filter_by(session_id=session_id).first()
    if pipeline_row is not None:
        bridge_rows = (
            db.query(RAGRetriever.id).filter(
                RAGRetriever.pipeline_id == pipeline_row[0]
            )
        ).all()
        for row in bridge_rows:
            bridge_ids.add(row[0])
    return IndexFootprint(
        chunk_set_ids=frozenset(chunk_set_ids),
        bridge_ids=frozenset(bridge_ids),
    )


def has_stale_index_rows(db: Session, session_id: int) -> bool:
    """Whether a session holds rows that a cleanup would release, without a rebuild.

    A healthy session has one pipeline root, the live tree, and one chunk set,
    the live one. More than one of either is left over from a cleanup that
    failed. A build that reused its index would never retry that cleanup, so the
    chat path asks this as well. It reads two counts and no tree, so it is cheap
    enough to ask on every turn.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    session_id : int
        The generative session to check.

    Returns
    -------
    bool
        ``True`` when the session owns more than one chunk set, or its pipeline
        has more than one root bridge.
    """
    chunk_set_count = (
        db.query(RAGChunkSet.id).filter(RAGChunkSet.session_id == session_id).count()
    )
    if chunk_set_count > 1:
        return True
    pipeline_row = db.query(RAGPipeline.id).filter_by(session_id=session_id).first()
    if pipeline_row is None:
        return False
    linked = select(RAGRetrieverChild.child_id)
    root_count = (
        db.query(RAGRetriever.id)
        .filter(
            RAGRetriever.pipeline_id == pipeline_row[0],
            RAGRetriever.id.not_in(linked),
        )
        .count()
    )
    return root_count > 1


def run_post_index_cleanup(
    db: Session,
    registry: ComponentRegistry,
    session_id: int,
    live_root_bridge_id: int | None,
    rag_path: str | Path,
) -> None:
    """Run the post-index cleanup for a session, without ever failing the caller.

    Called by the index and chat jobs once an index has been built. The index
    is already committed and complete by then, so a cleanup failure must not
    mark the job failed: the failure is logged with its traceback and the
    session is rolled back to a clean state. Cancellation and interpreter
    shutdown are ``BaseException``s and still propagate.

    Parameters
    ----------
    db : Session
        Session the cleanup runs in.
    registry : ComponentRegistry
        Component registry, passed through to :class:`CleanupService`.
    session_id : int
        The session that was just indexed.
    live_root_bridge_id : int | None
        Bridge id of the root of the retriever the index built. ``None`` is
        refused inside the guarded path, so it is logged rather than raised.
    rag_path : str | Path
        The RAG storage root (``RAG_PATH``). Removals are confined to it.
    """
    try:
        if live_root_bridge_id is None:
            raise ValueError(
                f"Session {session_id} has no live root bridge to clean up after; "
                "the index is kept and nothing is released."
            )
        summary = CleanupService(db, registry, rag_path=rag_path).cleanup_after_reindex(
            session_id, live_root_bridge_id
        )
    except Exception:
        db.rollback()
        log.exception(
            "Post-index cleanup failed for session %d; the index is kept.", session_id
        )
        return
    log.debug(
        "Post-index cleanup of session %d: %s",
        session_id,
        summary,
    )
