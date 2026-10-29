"""Shared rendering helpers for the retrieval evaluation prompt families.

Both the sufficiency and the filter prompts render the same numbered chunk
provenance lines and document summaries. Keeping the rendering here stops the
two families from drifting apart while leaving every prompt component in charge
of its own template and placeholder contract.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, List

from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CHUNK_DOCUMENT_ID,
    CHUNK_POSITION,
    CHUNK_TEXT,
    DOCUMENT_ID,
    DOCUMENT_NAME,
    ChunkPayload,
    DocumentSummary,
)

#: Maximum number of characters of each chunk's text rendered into a prompt.
CHUNK_TEXT_LIMIT = 400


def render_optional_value(value: Any) -> Any:
    """Render mapping/sequence placeholder values as indented JSON.

    Parameters
    ----------
    value : Any
        Placeholder value supplied by the caller.

    Returns
    -------
    Any
        Mappings and sequences become indented JSON strings; strings and scalars
        are returned unchanged so ``render_template`` still stringifies them and
        ``None`` keeps dropping the owning line.
    """
    if isinstance(value, Mapping):
        return json.dumps(dict(value), ensure_ascii=False, indent=2)
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), ensure_ascii=False, indent=2)
    return value


def format_chunks(chunks: str | Sequence[ChunkPayload]) -> str:
    """Render chunk provenance lines, or keep a preformatted string.

    Parameters
    ----------
    chunks : str | Sequence[Mapping[str, Any]]
        Either an already-rendered block (returned verbatim) or structured
        payloads carrying ``document_id``, ``position`` and ``text``.

    Returns
    -------
    str
        One ``[i] (document_id=..., position=...) <text>`` line per chunk.

    Raises
    ------
    RAGPromptTemplateError
        If a structured payload is not a mapping or misses a required key.
    """
    if isinstance(chunks, str):
        return chunks
    lines: List[str] = []
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, Mapping):
            raise RAGPromptTemplateError(
                f"Chunk payload {index} must be a mapping, got {type(chunk).__name__}."
            )
        missing: List[str] = []
        for key in (CHUNK_DOCUMENT_ID, CHUNK_POSITION, CHUNK_TEXT):
            if key not in chunk:
                missing.append(key)
        if missing:
            raise RAGPromptTemplateError(
                f"Chunk payload {index} is missing required keys: {', '.join(missing)}."
            )
        raw_text = str(chunk[CHUNK_TEXT])
        text = raw_text[:CHUNK_TEXT_LIMIT]
        if len(raw_text) > CHUNK_TEXT_LIMIT:
            text += "..."
        lines.append(
            f"[{index}] ({CHUNK_DOCUMENT_ID}={chunk[CHUNK_DOCUMENT_ID]}, "
            f"{CHUNK_POSITION}={chunk[CHUNK_POSITION]}) {text}"
        )
    return "\n".join(lines)


def format_documents(
    documents: Sequence[DocumentSummary] | None,
) -> tuple[str | None, str | None]:
    """Return the document names and JSON description for the prompt.

    Parameters
    ----------
    documents : Sequence[DocumentSummary] | None
        Structured document summaries supplied by the retrieval context.

    Returns
    -------
    tuple[str | None, str | None]
        The comma-separated display names and the JSON description, or
        ``(None, None)`` when no documents are supplied.
    """
    if not documents:
        return None, None
    names: List[str] = []
    for document in documents:
        name = document.get(DOCUMENT_NAME)
        if not name:
            name = f"document {document.get(DOCUMENT_ID)}"
        names.append(str(name))
    return ", ".join(names), render_optional_value(documents)


def render_template(
    template: str,
    required: dict[str, Any],
    optional: dict[str, Any] | None = None,
) -> str:
    """Render a template in the mandated order.

    Optional placeholders are resolved first, directly on the raw template
    (dropping whole lines when their value is ``None``); required placeholders
    are substituted afterwards in a single pass. Resolving the optionals first
    is what lets a user message or chunk that literally contains an optional
    token survive verbatim, and the single-pass required substitution stops
    inserted values from being re-expanded.

    Parameters
    ----------
    template : str
        The raw template.
    required : dict[str, Any]
        Mapping of required placeholder token to replacement value.
    optional : dict[str, Any] | None
        Mapping of optional placeholder token to replacement value. ``None``
        maps (or a ``None`` value) drop the token's lines.

    Returns
    -------
    str
        The rendered template.
    """
    buffer = template
    if optional:
        for key, value in optional.items():
            buffer = BasePrompt.render_optional(buffer, key, value)
    return BasePrompt.render_placeholders(buffer, required)
