import copy
import os
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from enum import Enum
from typing import Any, ClassVar, Dict, Final, List, Tuple

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk, RAGDocument
from DashAI.back.models.RAG.exceptions import RAGRetrieverError, RAGWorkflowError
from DashAI.back.models.RAG.retrievers.ref_utils import is_component_ref
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    SCHEMA_CHILDREN,
    SCHEMA_CLASS,
    SCHEMA_PARAMS,
    SchemaSummary,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND,
    DEFAULT_EXPAND_WINDOW,
    ENABLE_FIELD,
    EXPANDED_CHUNK_SEPARATOR,
    MAX_EXPAND_WINDOW,
    WINDOW_FIELD,
)

#: Sentinel returned when a schema-summary path cannot be resolved.
_UNRESOLVED: Final = object()

#: Maximum number of nested composite levels summarized before stopping.
_MAX_SCHEMA_SUMMARY_DEPTH: Final = 32


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable copy of ``value``.

    Enums are replaced by their ``.value``; lists, tuples and dicts are walked
    recursively; every other value (primitives included) is returned as-is.

    Parameters
    ----------
    value : Any
        Value to make JSON-serializable.

    Returns
    -------
    Any
        A JSON-serializable value with enum instances replaced by their values.
    """
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, dict):
        converted: Dict[Any, Any] = {}
        for key, item in value.items():
            converted[key] = _json_safe(item)
        return converted
    if isinstance(value, (list, tuple)):
        converted_list: List[Any] = []
        for item in value:
            converted_list.append(_json_safe(item))
        return converted_list
    return value


class BaseRetriever(ConfigObject, ABC):
    """
    Component: abstract base class for all retrievers.

    Implements the Component role in the Composite design pattern (GoF).
    """

    TYPE: Final[str] = "Retriever"
    DISPLAY_NAME: str = MultilingualString(
        en="Retriever",
        es="Recuperador",
        pt="Recuperador",
        de="Retriever",
        zh="检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Document retrieval component.",
        es="Componente de recuperación de documentos.",
        pt="Componente de recuperação de documentos.",
        de="Komponente zur Dokumentabfrage.",
        zh="文档检索组件。",
    )
    COLOR: str = "#9C27B0"
    ICON: str = "Search"
    CATEGORY: MultilingualString = MultilingualString(
        en="Other retrievers",
        es="Otros recuperadores",
        pt="Outros recuperadores",
        de="Andere Retriever",
        zh="其他检索器",
    )

    #: Per-retriever representation template rendered by the frontend.
    #: ``None`` means the frontend falls back to the component description.
    #: Placeholders follow this contract:
    #:
    #: * ``{param}`` resolves to a direct retriever parameter. When the
    #:   parameter is a component reference, the nested component class name
    #:   is rendered instead.
    #: * ``{nested.param}`` resolves to parameter ``param`` of the nested
    #:   component stored under ``nested``.
    #:
    #: The frontend tolerates missing values; the backend only supplies the
    #: template and never renders it.
    REPRESENTATION: ClassVar[MultilingualString | None] = None

    env_RAG_path: str | os.PathLike | None  # noqa: N815
    chunks: Dict[int, Dict[int, Chunk]]
    documents: Dict[int, RAGDocument]
    params: Dict[str, Any]

    @classmethod
    def get_representation(cls) -> MultilingualString | None:
        """Return the retriever's representation template, if any.

        Returns
        -------
        MultilingualString | None
            The template with ``{param}`` / ``{nested.param}`` placeholders,
            or ``None`` when the frontend should fall back to the component
            description.
        """
        return cls.REPRESENTATION

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return the UI metadata shared by every retriever.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the icon shown for the retriever in the frontend
            and, when declared, its representation template and the category
            the retriever pickers group it under.
        """
        metadata: Dict[str, Any] = {"icon": cls.ICON, "category": cls.CATEGORY}
        representation = cls.get_representation()
        if representation is not None:
            metadata["representation"] = representation
        parameters = cls.get_schema_summary_parameters()
        if parameters:
            metadata["schema_summary_parameters"] = parameters
        return metadata

    def __init__(self, **kwargs):
        """Initialize the retriever model.

        Stores keyword arguments as ``self.params`` and initialises the
        database ID to ``None``. The shared retrieve-then-expand options are
        popped from *kwargs*, validated and kept as attributes so they never
        leak into the technique-specific parameters.

        Args:
            **kwargs: Configuration parameters for the retriever.

        Raises:
            RAGRetrieverError: If ``enable_retrieve_then_expand`` is not a
                boolean, or ``expand_window`` is not an integer of at least
                one.
        """
        self._db_id: int | None = None
        self._trace_params: Dict[str, Any] = {}
        self.documents: Dict[int, RAGDocument] = {}
        enabled = kwargs.pop(ENABLE_FIELD, DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND)
        if not isinstance(enabled, bool):
            raise RAGRetrieverError(
                f"'{ENABLE_FIELD}' must be a boolean, got "
                f"{type(enabled).__name__} {enabled!r}."
            )
        window = kwargs.pop(WINDOW_FIELD, DEFAULT_EXPAND_WINDOW)
        if (
            isinstance(window, bool)
            or not isinstance(window, int)
            or not 1 <= window <= MAX_EXPAND_WINDOW
        ):
            raise RAGRetrieverError(
                f"'{WINDOW_FIELD}' must be an integer in "
                f"[1, {MAX_EXPAND_WINDOW}], got {window!r}."
            )
        self.enable_retrieve_then_expand: bool = enabled
        self.expand_window: int = window
        self.params = kwargs

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Return the display label -> dotted configuration path mapping.

        This is the single source of truth for the schema summary: the frontend
        receives the same mapping through ``schema_summary_parameters`` in the
        metadata, while :meth:`get_schema_summary` resolves each path against
        the live instance.

        Returns
        -------
        Dict[str, str]
            The retriever's summary parameters (empty by default).
        """
        return {}

    @classmethod
    def get_schema_summary_parameters(cls) -> Dict[str, str]:
        """Return a copy of the summary parameter mapping for the frontend."""
        return dict(cls._get_main_parameters())

    def _resolve_first_segment(self, segment: str) -> Any:
        """Resolve a first path segment from trace params, params or attributes.

        ``_top_k`` is the one summary value stored under a private attribute
        (the public ``top_k`` is popped during construction), so it is resolved
        as a fallback when no raw configuration snapshot is available.

        Parameters
        ----------
        segment : str
            First segment of a dotted summary path.

        Returns
        -------
        Any
            The resolved value, or ``_UNRESOLVED`` when the segment is unknown.
        """
        for source in (self._trace_params, self.params):
            if segment in source:
                return source[segment]
        value = getattr(self, segment, _UNRESOLVED)
        if value is _UNRESOLVED:
            value = getattr(self, f"_{segment}", _UNRESOLVED)
        return value

    @staticmethod
    def _resolve_next_segment(value: Any, segment: str) -> Any:
        """Resolve a nested segment through component refs, dicts or attributes.

        Parameters
        ----------
        value : Any
            Current value in the path resolution.
        segment : str
            Next segment to resolve.

        Returns
        -------
        Any
            The resolved value, or ``_UNRESOLVED`` when it cannot be resolved.
        """
        if is_component_ref(value):
            value = value.get("params") or {}
        if isinstance(value, dict):
            return value.get(segment, _UNRESOLVED)
        return getattr(value, segment, _UNRESOLVED)

    def _resolve_parameter(self, path: str) -> Any:
        """Resolve a dotted parameter path against the live instance.

        Parameters
        ----------
        path : str
            Dotted configuration path (for example
            ``"embedding_model.model_name"``).

        Returns
        -------
        Any
            The resolved value, or ``_UNRESOLVED`` when any segment is unknown.
        """
        segments: List[str] = []
        for segment in path.split("."):
            if segment:
                segments.append(segment)
        if not segments:
            return _UNRESOLVED
        value = self._resolve_first_segment(segments[0])
        for segment in segments[1:]:
            if value is _UNRESOLVED:
                return _UNRESOLVED
            value = self._resolve_next_segment(value, segment)
        return value

    def _get_schema_summary(self, depth: int) -> SchemaSummary:
        """Build the recursive schema summary at a bounded nesting depth.

        This is the protected recursion hook: nested composites call it
        directly with ``depth + 1`` instead of restarting at zero.

        Parameters
        ----------
        depth : int
            Current nesting depth. Children are summarized at ``depth + 1`` and
            recursion stops once ``_MAX_SCHEMA_SUMMARY_DEPTH`` is reached.

        Returns
        -------
        SchemaSummary
            ``{"class": ..., "params": ...}`` plus ``children`` when present.
        """
        params: Dict[str, Any] = {}
        for label, path in type(self).get_schema_summary_parameters().items():
            value = self._resolve_parameter(path)
            if value is _UNRESOLVED or value is None:
                continue
            params[label] = _json_safe(value)
        summary: SchemaSummary = {
            SCHEMA_CLASS: type(self).__name__,
            SCHEMA_PARAMS: params,
        }
        if depth >= _MAX_SCHEMA_SUMMARY_DEPTH:
            return summary
        try:
            children = self.get_children()
        except NotImplementedError:
            children = []
        if children:
            child_summaries: List[SchemaSummary] = []
            for child in children:
                child_summaries.append(child._get_schema_summary(depth + 1))
            summary[SCHEMA_CHILDREN] = child_summaries
        return summary

    def get_schema_summary(self) -> SchemaSummary:
        """Return a recursive, JSON-serializable summary of this retriever.

        Each declared label is resolved against the live instance and omitted
        when its path cannot be resolved. Composite retrievers also nest their
        children's summaries under ``children``; unit retrievers omit that key.

        Returns
        -------
        SchemaSummary
            ``{"class": ..., "params": ...}`` plus ``children`` when present.
        """
        return self._get_schema_summary(0)

    def set_trace_params(self, params: Dict[str, Any]) -> None:
        """Store a JSON-serializable snapshot of this retriever's configuration.

        Parameters
        ----------
        params : Dict[str, Any]
            Raw construction parameters captured by the factory before any
            nested component reference is consumed. A deep copy is stored so
            later mutations of the original mapping cannot affect trace
            rendering.
        """
        self._trace_params = copy.deepcopy(params)

    def get_id(self) -> int | None:
        """Return the database ID of this retriever, or ``None``.

        Returns:
            The database ID if already persisted, otherwise ``None``.
        """
        return self._db_id

    def set_id(self, id: int) -> None:
        """Assign a database ID to this retriever.

        The ID can only be set once; subsequent calls raise an error.

        Args:
            id: The database ID to assign.

        Raises:
            RAGWorkflowError: If an ID has already been assigned.
        """
        if self._db_id is not None:
            raise RAGWorkflowError(
                f"ID is already set to {self._db_id}, cannot reassign to {id}."
            )
        self._db_id = id

    def _validate_chunks_dict(self) -> None:
        """Validate the structure of the ``chunks`` attribute.

        Ensures it is a nested dictionary of the form
        ``{doc_id: {chunk_id: Chunk}}`` and that each chunk's
        ``document_id`` matches its parent key.

        Raises:
            ValueError: If the structure is invalid.
        """
        if not isinstance(self.chunks, dict):
            raise ValueError("Chunks must be a dictionary.")
        for doc_id, doc_chunks in self.chunks.items():
            if not isinstance(doc_id, int):
                raise ValueError(f"Document ID {doc_id} must be an integer.")
            if not isinstance(doc_chunks, dict):
                raise ValueError(
                    f"Chunks for document ID {doc_id} must be a dictionary."
                )
            for chunk_id, chunk in doc_chunks.items():
                if not isinstance(chunk_id, int):
                    raise ValueError(
                        f"Chunk ID {chunk_id} in document ID {doc_id}"
                        f" must be an integer."
                    )
                if not isinstance(chunk, Chunk):
                    raise ValueError(
                        f"Chunk {chunk_id} in document ID {doc_id}"
                        f" must be an instance of Chunk."
                    )
                if chunk.document_id != doc_id:
                    raise ValueError(
                        f"Chunk {chunk_id} document_id {chunk.document_id}"
                        f" != doc ID {doc_id}."
                    )

    def inject_infra(
        self,
        env_RAG_path: str | os.PathLike,  # noqa: N803
        chunks: Dict[int, Dict[int, Chunk]],
        persistence: Any,
        documents: Dict[int, RAGDocument] | None = None,
    ) -> None:
        """Inject runtime infrastructure *after* schema validation.

        Subclasses **must** store the arguments as instance attributes.  Raises
        ``TypeError`` if any argument has an unexpected type.

        Subclasses define required params in their ``__init__`` and
        pop them from ``self.params``.

        Args:
            env_RAG_path: Root directory path for RAG data.
            chunks: Nested dictionary mapping document IDs to chunk IDs
                to :class:`Chunk` instances.
            persistence: Persistence object for saving/loading state.
            documents: Optional document mapping used by the LLM-evaluated
                retrievers to describe the corpus in their prompts.
        """
        self.env_RAG_path = env_RAG_path
        self.chunks = chunks
        self._persistence = persistence
        self.documents = documents or {}
        self._validate_chunks_dict()

    @property
    def persistence(self):
        """Get the persistence object."""
        return self._persistence

    @persistence.setter
    def persistence(self, value):
        """Set the persistence object.

        Args:
            value: The new persistence object.
        """
        self._persistence = value

    # Retrieve-then-expand

    def _window_bounds(
        self, positions: List[int], position: int, window_size: int
    ) -> Tuple[int, int]:
        """Return the inclusive document-position range of a centred window.

        Positions may have gaps, so the start is resolved in position space and
        then mapped back to the sorted chunk list. The window is shifted back at
        the end of the document to keep it full when there are enough chunks.

        Args:
            positions: Non-empty sorted document positions.
            position: Position the window is centred on.
            window_size: Number of stored chunks the window should cover.
        """
        total = len(positions)
        if total <= window_size:
            return positions[0], positions[-1]
        start_position = max(positions[0], position - (window_size - 1) // 2)
        start = min(bisect_left(positions, start_position), total - window_size)
        return positions[start], positions[start + window_size - 1]

    def _build_expanded_chunk(
        self,
        document_id: int,
        ordered: List[Chunk],
        positions: List[int],
        start: int,
        end: int,
    ) -> Chunk | None:
        """Build a chunk covering the stored chunks between *start* and *end*.

        Args:
            document_id: Document the chunks belong to.
            ordered: Document chunks sorted by position.
            positions: Sorted document positions, aligned with *ordered*.
            start: First covered document position (not a list index).
            end: Last covered document position, inclusive.
        """
        selected = ordered[bisect_left(positions, start) : bisect_right(positions, end)]
        if not selected:
            return None
        first = selected[0]
        if len(selected) == 1:
            return first
        return Chunk(
            id=first.id,
            document_id=document_id,
            document_position=first.document_position,
            text=EXPANDED_CHUNK_SEPARATOR.join(chunk.text for chunk in selected),
            page=first.page,
            source_positions=tuple(chunk.document_position for chunk in selected),
        )

    def _merge_chunks(
        self, chunks: List[Chunk], window_size: int | None
    ) -> List[Chunk]:
        """Expand plain chunks and merge overlapping covered ranges.

        ``window_size=None`` only merges chunks that already carry
        ``source_positions``. Plain chunks inside a merged range are absorbed by
        it, while chunks outside every range are returned unchanged. The
        injected corpus and the input list are never mutated.
        """
        corpus = getattr(self, "chunks", None) or {}
        if not corpus:
            return chunks

        ordered_by_document: Dict[int, List[Chunk]] = {}
        positions_by_document: Dict[int, List[int]] = {}
        for document_id, document_chunks in corpus.items():
            ordered = sorted(
                document_chunks.values(),
                key=lambda chunk: chunk.document_position,
            )
            ordered_by_document[document_id] = ordered
            positions_by_document[document_id] = [
                chunk.document_position for chunk in ordered
            ]

        # Each range: (document_id, start, end, first_retrieval_order, fixed_chunk)
        ranges: List[Tuple[int, int, int, int, Chunk | None]] = []
        passthrough: List[Tuple[int, Chunk]] = []
        for order, chunk in enumerate(chunks):
            ordered = ordered_by_document.get(chunk.document_id)
            if not ordered:
                passthrough.append((order, chunk))
                continue
            positions = positions_by_document[chunk.document_id]
            covered = getattr(chunk, "source_positions", None)
            if covered:
                start, end, fixed = min(covered), max(covered), chunk
            elif window_size is None:
                start = end = chunk.document_position
                fixed = chunk
            else:
                index = bisect_left(positions, chunk.document_position)
                if (
                    index == len(positions)
                    or positions[index] != chunk.document_position
                ):
                    passthrough.append((order, chunk))
                    continue
                start, end = self._window_bounds(
                    positions, chunk.document_position, window_size
                )
                fixed = None
            ranges.append((chunk.document_id, start, end, order, fixed))

        ranges_by_document: Dict[
            int, List[Tuple[int, int, int, int, Chunk | None]]
        ] = {}
        for item in ranges:
            ranges_by_document.setdefault(item[0], []).append(item)

        merged: List[Tuple[int, int, int, int, Chunk | None]] = []
        for document_ranges in ranges_by_document.values():
            document_ranges.sort(key=lambda item: item[1])
            current = list(document_ranges[0])
            for candidate in document_ranges[1:]:
                if candidate[1] <= current[2]:
                    current[2] = max(current[2], candidate[2])
                    current[3] = min(current[3], candidate[3])
                    current[4] = None
                else:
                    merged.append(tuple(current))
                    current = list(candidate)
            merged.append(tuple(current))

        result: List[Tuple[int, Chunk]] = list(passthrough)
        for document_id, start, end, order, fixed in merged:
            built = fixed
            if built is None:
                built = self._build_expanded_chunk(
                    document_id,
                    ordered_by_document[document_id],
                    positions_by_document[document_id],
                    start,
                    end,
                )
            if built is not None:
                result.append((order, built))
        result.sort(key=lambda item: item[0])
        return [chunk for _, chunk in result]

    def expand_retrieved_chunks(
        self, chunks: List[Chunk], window_size: int
    ) -> List[Chunk]:
        """Expand *chunks* into centred windows and merge overlapping windows.

        Raises:
            RAGRetrieverError: If ``window_size`` is not an integer in
                ``[1, MAX_EXPAND_WINDOW]``.
        """
        if (
            isinstance(window_size, bool)
            or not isinstance(window_size, int)
            or not 1 <= window_size <= MAX_EXPAND_WINDOW
        ):
            raise RAGRetrieverError(
                f"'{WINDOW_FIELD}' must be an integer in "
                f"[1, {MAX_EXPAND_WINDOW}], got {window_size!r}."
            )
        if window_size <= 1:
            return list(chunks)
        return self._merge_chunks(chunks, window_size)

    def merge_expanded_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Merge overlapping expanded units without widening plain chunks."""
        if not any(getattr(chunk, "source_positions", None) for chunk in chunks):
            return chunks
        return self._merge_chunks(chunks, None)

    def _apply_retrieval_expansion(self, chunks: List[Chunk]) -> List[Chunk]:
        """Apply retrieve-then-expand to a retriever's final output."""
        if not getattr(self, "enable_retrieve_then_expand", False):
            return self.merge_expanded_chunks(chunks)
        if not getattr(self, "chunks", None):
            return chunks
        window = getattr(self, "expand_window", DEFAULT_EXPAND_WINDOW)
        if window <= 1:
            return self.merge_expanded_chunks(chunks)
        return self.expand_retrieved_chunks(chunks, window)

    def init_model(self) -> None:
        """Called by the factory **after** ``inject_infra()``.

        Subclasses restore saved state (``load()``) or compute initial
        state (``_fit()``, ``_init_embedding()``).  Default is a no-op.
        """

    def close(self) -> None:
        """Release resources owned by this retriever.

        Lifecycle hook called by the pipeline when the retrieval stage ends.
        The default implementation does nothing; subclasses holding a model
        override it and must keep the call idempotent.

        Returns
        -------
        None
            Nothing.
        """

    @abstractmethod
    def retrieve(self, query, **kwargs) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve the top-k chunks most relevant to the query.

        Args:
            query: The search query string.
            **kwargs: Additional retrieval parameters (e.g. ``top_k``).

        Returns:
            A ``(chunks, trace)`` tuple. ``chunks`` is a list of
            :class:`Chunk` instances ordered by relevance. ``trace`` is a
            JSON-serializable trace node describing this retriever's run:
            ``{"name": <component class name>, "chunks": [<chunk refs>],
            "children": [<child trace nodes>], ...}`` where the chunk refs use
            the ``"<document_id>_<position>"`` format (the join key with the
            pipeline's Dict output row). Composites nest their children's nodes
            under ``children``; unit retrievers omit ``children``. Techniques
            may add extra keys (e.g. the cross-encoder adds ``scores``).
        """
        raise NotImplementedError

    @abstractmethod
    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Score a set of chunks against a query.

        Args:
            chunk_ids: List of chunk IDs to score.
            query: The search query string.

        Returns:
            A list of ``(chunk_id, distance)`` tuples sorted by distance
            (ascending — lower is more relevant).
        """
        raise NotImplementedError

    @property
    def retrieval_top_k(self) -> int:
        """Return the maximum number of chunks this retriever returns.

        Returns:
            The top-k value.
        """
        raise NotImplementedError

    # ── Child management (Composite pattern) ────────────────────────

    def add(self, child: "BaseRetriever") -> None:
        """Add a child retriever (Composite pattern).

        Args:
            child: The child retriever to add.

        Raises:
            NotImplementedError: If the subclass does not support children.
        """
        raise NotImplementedError

    def remove(self, child: "BaseRetriever") -> None:
        """Remove a child retriever (Composite pattern).

        Args:
            child: The child retriever to remove.

        Raises:
            NotImplementedError: If the subclass does not support children.
        """
        raise NotImplementedError

    def get_children(self) -> List["BaseRetriever"]:
        """Return the list of child retrievers (Composite pattern).

        Returns:
            A list of :class:`BaseRetriever` children.

        Raises:
            NotImplementedError: If the subclass does not support children.
        """
        raise NotImplementedError

    def save(self, filename: str = "") -> None:
        """Persist the retriever's state to disk.

        Args:
            filename: Optional filename override. Defaults to an empty
                string (subclasses determine their own default path).
        """

    def load(self, filename: str = "") -> None:
        """Restore the retriever's state from disk.

        Args:
            filename: Optional filename override. Defaults to an empty
                string (subclasses determine their own default path).
        """
