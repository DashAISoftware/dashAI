"""Strict parser for the LLM filter selection contract.

The LLM filter retriever asks its language model to return the 1-based indices
of the best candidate chunks. Surrounding prose and markdown fences are
tolerated, but the selection itself is strict: selecting the same index twice,
an out-of-range or non-integer index, or more than ``top_k`` entries rejects the
whole selection. The caller retries the entire model call + parse, so a
partially valid selection is never applied.

Contract
--------
``{"selected_chunks": [<1-based candidate index>], "message": "...",
"justification": "..."}``

``selected_chunks`` is required and must contain 1 to ``top_k`` unique, in-range
candidate indices. ``message`` and ``justification`` are optional, lenient
narrative fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, List

from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.retrievers.composite.structured_output import (
    cap_errors,
    coerce_int,
    optional_text,
    parse_json_object,
    preview,
    preview_value,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    SELECTED_CHUNKS_KEY,
)


@dataclass(frozen=True)
class ChunkSelection:
    """A validated chunk selection returned by the filter model.

    Attributes
    ----------
    selected_indices : tuple[int, ...]
        The chosen 1-based candidate indices, in the model's order (best first).
    message : str
        Optional short, user-facing status sentence. Empty when the model did
        not supply one.
    justification : str
        Optional short rationale for the selection. Empty when the model did not
        supply one.
    dropped_operations : tuple[str, ...]
        Kept for trace compatibility. Always empty: invalid selections reject
        the whole decision instead of dropping entries.
    """

    selected_indices: tuple[int, ...]
    message: str = ""
    justification: str = ""
    dropped_operations: tuple[str, ...] = ()


def _validate_indices(
    raw_indices: List[Any],
    *,
    top_k: int,
    candidate_count: int,
) -> List[int]:
    """Validate the raw selection entries strictly.

    Parameters
    ----------
    raw_indices : List[Any]
        Raw ``selected_chunks`` list from the decoded payload.
    top_k : int
        Maximum number of indices that may be selected.
    candidate_count : int
        Number of numbered candidates the indices may address.

    Returns
    -------
    List[int]
        The unique, in-range indices in model order.

    Raises
    ------
    RAGRetrieverEvaluationError
        If any entry is a boolean, a non-integer, out of range or duplicated, or
        if the selection contains more than ``top_k`` entries.
    """
    selected: List[int] = []
    errors: List[str] = []
    for raw_index in raw_indices:
        index = coerce_int(raw_index, 1, allow_digit_string=True)
        if index is None:
            errors.append(
                f"'{SELECTED_CHUNKS_KEY}' entry {preview_value(raw_index)}: "
                "candidate indices must be integers greater than or equal to 1"
            )
            continue
        if index > candidate_count:
            errors.append(
                f"'{SELECTED_CHUNKS_KEY}' index {index} is outside the "
                f"1..{candidate_count} candidate range"
            )
            continue
        if index in selected:
            errors.append(f"'{SELECTED_CHUNKS_KEY}' index {index} is duplicated")
            continue
        selected.append(index)
    if errors:
        raise RAGRetrieverEvaluationError(
            "Invalid filter selection: " + "; ".join(cap_errors(errors)) + "."
        )
    if not selected:
        raise RAGRetrieverEvaluationError(
            f"'{SELECTED_CHUNKS_KEY}' must contain at least one candidate index."
        )
    if len(selected) > top_k:
        raise RAGRetrieverEvaluationError(
            f"'{SELECTED_CHUNKS_KEY}' contains {len(selected)} indices but the "
            f"top_k limit is {top_k}."
        )
    return selected


def _validate_selection(
    parsed: Any,
    raw: Any,
    *,
    top_k: int,
    candidate_count: int,
) -> ChunkSelection:
    """Validate a decoded selection against the strict filter contract.

    Parameters
    ----------
    parsed : Any
        The decoded selection payload, expected to be a mapping.
    raw : Any
        Original payload, echoed in error messages.
    top_k : int
        Maximum number of indices that may be selected.
    candidate_count : int
        Number of numbered candidates the indices may address.

    Returns
    -------
    ChunkSelection
        The validated selection with ``dropped_operations`` empty.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the payload is not a mapping, ``selected_chunks`` is missing or is
        not a list, or any index is invalid.
    """
    if not isinstance(parsed, Mapping):
        raise RAGRetrieverEvaluationError(
            f"The filter output is not a JSON object. Preview: {preview(raw)}"
        )
    if SELECTED_CHUNKS_KEY not in parsed:
        raise RAGRetrieverEvaluationError(
            f"'{SELECTED_CHUNKS_KEY}' is required. Preview: {preview(raw)}"
        )
    raw_indices = parsed[SELECTED_CHUNKS_KEY]
    if not isinstance(raw_indices, list):
        raise RAGRetrieverEvaluationError(
            f"'{SELECTED_CHUNKS_KEY}' must be a list of candidate indices, got "
            f"{type(raw_indices).__name__}. Preview: {preview(raw)}"
        )

    selected = _validate_indices(
        raw_indices, top_k=top_k, candidate_count=candidate_count
    )
    return ChunkSelection(
        selected_indices=tuple(selected),
        message=optional_text(parsed, RAG_PROGRESS_MESSAGE_KEY),
        justification=optional_text(parsed, RAG_PROGRESS_JUSTIFICATION_KEY),
        dropped_operations=(),
    )


def parse_filter_output(
    raw: str,
    *,
    top_k: int,
    candidate_count: int,
) -> ChunkSelection:
    """Parse the filter selection out of raw model output.

    Markdown fences are stripped, the substring from the first ``{`` to the last
    ``}`` is taken, and the result must be a JSON object carrying a
    ``selected_chunks`` list.

    Parameters
    ----------
    raw : str
        Raw model output.
    top_k : int
        Maximum number of indices that may be selected.
    candidate_count : int
        Number of numbered candidates the indices may address.

    Returns
    -------
    ChunkSelection
        The validated selection.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the output contains no JSON object, the JSON is invalid, or the
        decoded payload violates the selection contract.
    """
    parsed = parse_json_object(
        raw,
        no_object_message="The filter model output does not contain a JSON object.",
        parse_error_label="filter output",
    )
    return _validate_selection(
        parsed, raw, top_k=top_k, candidate_count=candidate_count
    )


def parse_filter_arguments(
    arguments: Any,
    *,
    top_k: int,
    candidate_count: int,
) -> ChunkSelection:
    """Validate the arguments payload of a filter function call.

    Function-calling backends return arguments either already decoded as a
    mapping or as a JSON-encoded string emitted under constrained sampling. Both
    are accepted here and validated against the same strict contract, so the two
    argument encodings cannot diverge.

    Parameters
    ----------
    arguments : Any
        The raw ``FunctionCallResult.arguments`` payload.
    top_k : int
        Maximum number of indices that may be selected.
    candidate_count : int
        Number of numbered candidates the indices may address.

    Returns
    -------
    ChunkSelection
        The validated selection.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the payload is a string that fails text parsing, is a mapping that
        violates the contract, or is neither a mapping nor a string.
    """
    if isinstance(arguments, Mapping):
        return _validate_selection(
            arguments, arguments, top_k=top_k, candidate_count=candidate_count
        )
    if isinstance(arguments, str):
        return parse_filter_output(
            arguments, top_k=top_k, candidate_count=candidate_count
        )
    raise RAGRetrieverEvaluationError(
        "The filter function-call arguments must be a mapping or a JSON-encoded "
        f"string, got {type(arguments).__name__}. Preview: {preview(arguments)}"
    )
