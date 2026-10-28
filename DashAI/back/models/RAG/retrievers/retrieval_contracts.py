"""Typed payload contracts shared by the retrieval evaluation collaborators.

Keeping the field names in one module stops the context, the evaluator and the
prompt components from drifting apart.
"""

from __future__ import annotations

from typing import Any, Dict, List, NotRequired, Tuple, TypedDict

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions.retriever import RAGRetrieverError

#: Structured chunk payload field names.
CHUNK_DOCUMENT_ID = "document_id"
CHUNK_POSITION = "position"
CHUNK_TEXT = "text"

#: Structured document summary field names.
DOCUMENT_ID = "document_id"
DOCUMENT_NAME = "name"
DOCUMENT_CHUNKS = "chunks"
DOCUMENT_PAGES = "pages"

#: Schema summary field names.
SCHEMA_CLASS = "class"
SCHEMA_PARAMS = "params"
SCHEMA_CHILDREN = "children"

#: Canonical retrieval-evaluation verdict field names.
SUFFICIENT_KEY = "sufficient"
CALL_RETRIEVERS_KEY = "call_retrievers"
REQUEST_CHUNKS_KEY = "request_specific_chunks"
DISCARD_KEY = "discard_specific_chunks"

#: Canonical LLM filter selection field name.
SELECTED_CHUNKS_KEY = "selected_chunks"

#: Key carrying the human-readable operations dropped while evaluating.
DROPPED_OPERATIONS_KEY = "dropped_operations"


class ChunkPayload(TypedDict):
    """One chunk as shown to the evaluation prompt."""

    document_id: int
    position: int
    text: str


class DocumentSummary(TypedDict):
    """One document summary as shown to the evaluation prompt."""

    document_id: int
    name: str | None
    chunks: int
    pages: int


SchemaSummary = TypedDict(
    "SchemaSummary",
    {
        SCHEMA_CLASS: str,
        SCHEMA_PARAMS: Dict[str, Any],
        SCHEMA_CHILDREN: NotRequired[List["SchemaSummary"]],
    },
)

#: 1-based retriever index to its recursive schema summary.
RetrieverCatalog = Dict[int, SchemaSummary]


def unpack_retrieval_result(result: Any) -> Tuple[List[Chunk], Dict[str, Any]]:
    """Split a retriever's ``(chunks, trace)`` result, rejecting anything else.

    Every ``retrieve()`` returns a two-tuple: the ranked chunks and a trace
    node. A bare list of exactly two chunks would unpack silently into
    ``(chunks, trace)`` and corrupt the trace, so every composite that calls a
    child (including a plugin) goes through this guard instead of unpacking
    directly.

    Parameters
    ----------
    result : Any
        Whatever the child's ``retrieve()`` returned.

    Returns
    -------
    Tuple[List[Chunk], Dict[str, Any]]
        The chunks and the trace node.

    Raises
    ------
    RAGRetrieverError
        If the result is not a ``(list, dict)`` two-tuple.
    """
    if (
        not isinstance(result, tuple)
        or len(result) != 2
        or not isinstance(result[0], list)
        or not isinstance(result[1], dict)
    ):
        raise RAGRetrieverError(
            "retrieve() must return a (List[Chunk], Dict) tuple, got "
            f"{type(result).__name__}."
        )
    return result
