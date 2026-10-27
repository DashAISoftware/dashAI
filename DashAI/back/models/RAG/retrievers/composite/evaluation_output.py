"""Strict parser for the retrieval-evaluation verdict contract.

The LLM-evaluated retrievers ask their language model for a single JSON verdict
that judges whether the retrieved pool is sufficient and, when it is not, how to
proceed. The parser tolerates surrounding prose and markdown fences, but the
verdict itself is strict: any invalid retriever index, chunk position, duplicate
or contradictory operation rejects the whole verdict. The caller retries the
entire model call + parse + validation, so a partially valid decision is never
applied.

Contract
--------
``{"sufficient": true}`` — the pool answers the query.

An insufficient verdict carries any combination of:

* ``call_retrievers`` — ``{<1-based retriever index>: <top_k>}``;
* ``request_specific_chunks`` — ``{<document id>: [<chunk positions>]}``;
* ``discard_specific_chunks`` — ``{<document id>: [<chunk positions>]}``.

Requested and discarded chunks persist across rounds and can override each
other (the last action wins). A chunk listed in both fields of one verdict is
invalid and rejects the verdict. An insufficient verdict with no action is also
invalid: it cannot make progress.

A verdict may also carry two optional narrative fields:

* ``message`` — a short, one-sentence user-facing status;
* ``justification`` — a short rationale for the decision.

Both default to ``""`` when omitted. They are ancillary: a non-string value
(including JSON ``null``) is ignored rather than rejected, because model drift
in a cosmetic field must never abort retrieval. ``sufficient`` remains strictly
required.

Unknown keys are tolerated; the contract fields are not.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

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
    CALL_RETRIEVERS_KEY,
    DISCARD_KEY,
    DROPPED_OPERATIONS_KEY,
    REQUEST_CHUNKS_KEY,
    SUFFICIENT_KEY,
)

# Re-exported so existing imports keep working.
__all__ = [
    "CALL_RETRIEVERS_KEY",
    "DISCARD_KEY",
    "DROPPED_OPERATIONS_KEY",
    "REQUEST_CHUNKS_KEY",
    "SUFFICIENT_KEY",
    "RetrievalVerdict",
    "cap_dropped_operations",
    "has_actions",
    "parse_evaluation_arguments",
    "parse_evaluation_output",
    "require_planning_calls",
    "validate_call_indices",
]

#: Maximum number of dropped-operation messages retained in a verdict/trace.
_MAX_DROPPED_OPERATIONS = 50

#: Recognizes the synthetic summary produced when a drop list is capped.
_DROPPED_SUMMARY_RE = re.compile(r"^Dropped (\d+) more invalid operation\(s\)\.$")

#: Local aliases keep the parser's internal call sites terse.
_preview = preview
_preview_value = preview_value


@dataclass(frozen=True)
class RetrievalVerdict:
    """A validated retrieval-sufficiency verdict.

    Attributes
    ----------
    sufficient : bool
        Whether the accumulated pool answers the query.
    call_retrievers : Dict[int, int]
        Mapping of 1-based retriever index to the number of chunks to retrieve
        from it next. Empty when no retriever call is requested.
    request_specific_chunks : Dict[int, List[int]]
        Mapping of document id to chunk positions to include in the pool. Empty
        when no chunk is explicitly requested.
    discard_specific_chunks : Dict[int, List[int]]
        Mapping of document id to chunk positions to exclude from the pool.
        Empty when no chunk is discarded.
    message : str
        Optional short, user-facing status sentence. Empty when the model did
        not supply one.
    justification : str
        Optional short rationale for the verdict. Empty when the model did not
        supply one.
    dropped_operations : Tuple[str, ...]
        Kept for trace compatibility. Always empty: an invalid operation rejects
        the whole verdict and is retried instead of being dropped.
    """

    sufficient: bool
    call_retrievers: Dict[int, int] = field(default_factory=dict)
    request_specific_chunks: Dict[int, List[int]] = field(default_factory=dict)
    discard_specific_chunks: Dict[int, List[int]] = field(default_factory=dict)
    message: str = ""
    justification: str = ""
    dropped_operations: Tuple[str, ...] = ()


def cap_dropped_operations(drops: List[str]) -> List[str]:
    """Bound the number of retained drop messages.

    Parameters
    ----------
    drops : List[str]
        Raw drop messages in first-seen order.

    Returns
    -------
    List[str]
        At most ``_MAX_DROPPED_OPERATIONS`` messages in total. When more were
        supplied, the last retained entry is a summary of the omitted tail.
    """
    messages: List[str] = []
    omitted = 0
    for message in drops:
        match = _DROPPED_SUMMARY_RE.match(message)
        if match is None:
            messages.append(message)
            continue
        omitted += int(match.group(1))
    total = len(messages) + omitted
    if total <= _MAX_DROPPED_OPERATIONS:
        if omitted:
            messages.append(f"Dropped {omitted} more invalid operation(s).")
        return messages
    capped = messages[: _MAX_DROPPED_OPERATIONS - 1]
    capped.append(f"Dropped {total - len(capped)} more invalid operation(s).")
    return capped


def _drop_empty_documents(mapping: Dict[int, List[int]]) -> Dict[int, List[int]]:
    """Return a copy without document entries that have no positions.

    Parameters
    ----------
    mapping : Dict[int, List[int]]
        Document id to chunk positions.

    Returns
    -------
    Dict[int, List[int]]
        Only the document ids that still carry at least one position.
    """
    cleaned: Dict[int, List[int]] = {}
    for document_id, positions in mapping.items():
        if positions:
            cleaned[document_id] = positions
    return cleaned


def _validate_call_retrievers(value: Any) -> Dict[int, int]:
    """Validate the ``call_retrievers`` mapping strictly.

    Parameters
    ----------
    value : Any
        Raw ``call_retrievers`` value from the parsed verdict.

    Returns
    -------
    Dict[int, int]
        1-based retriever index to requested chunk count.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the value is not a mapping, or any index or top_k is invalid or
        duplicated. No partial result is returned.
    """
    if not isinstance(value, Mapping):
        raise RAGRetrieverEvaluationError(
            f"'{CALL_RETRIEVERS_KEY}' must be a mapping of retriever index to "
            f"top_k, got {type(value).__name__}."
        )
    calls: Dict[int, int] = {}
    errors: List[str] = []
    for raw_index, raw_top_k in value.items():
        index = coerce_int(raw_index, 1, allow_digit_string=True)
        if index is None:
            errors.append(
                f"'{CALL_RETRIEVERS_KEY}' entry {_preview_value(raw_index)}: "
                "retriever index must be an integer greater than or equal to 1."
            )
            continue
        if index in calls:
            errors.append(
                f"'{CALL_RETRIEVERS_KEY}' duplicate entry for retriever index {index}."
            )
            continue
        top_k = coerce_int(raw_top_k, 1, allow_digit_string=False)
        if top_k is None:
            errors.append(
                f"'{CALL_RETRIEVERS_KEY}' entry {index}: top_k must be an "
                "integer greater than or equal to 1."
            )
            continue
        calls[index] = top_k
    if errors:
        raise RAGRetrieverEvaluationError(
            "Invalid retriever call(s) in the decision: "
            + "; ".join(cap_errors(errors))
        )
    return calls


def _validate_chunk_map(value: Any, key: str) -> Dict[int, List[int]]:
    """Validate one document-to-positions mapping strictly.

    Repeated positions inside one document are deduplicated (not a semantic
    failure), and document ids that collide after coercion union their
    positions. Any malformed entry rejects the whole map.

    Parameters
    ----------
    value : Any
        Raw mapping from the parsed verdict.
    key : str
        Canonical contract field name, echoed in error messages.

    Returns
    -------
    Dict[int, List[int]]
        Document id to chunk positions in first-seen order.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the value is not a mapping, or any document id or position is invalid.
    """
    if not isinstance(value, Mapping):
        raise RAGRetrieverEvaluationError(
            f"'{key}' must be a mapping of document id to chunk positions, got "
            f"{type(value).__name__}."
        )
    chunks: Dict[int, List[int]] = {}
    errors: List[str] = []
    for raw_document_id, raw_positions in value.items():
        document_id = coerce_int(raw_document_id, 0, allow_digit_string=True)
        if document_id is None:
            errors.append(
                f"'{key}' entry {_preview_value(raw_document_id)}: document id "
                "must be an integer greater than or equal to 0."
            )
            continue
        if not isinstance(raw_positions, list):
            errors.append(
                f"'{key}' document {document_id}: positions must be a list, got "
                f"{type(raw_positions).__name__}."
            )
            continue
        positions = chunks.setdefault(document_id, [])
        for raw_position in raw_positions:
            position = coerce_int(raw_position, 0, allow_digit_string=False)
            if position is None:
                errors.append(
                    f"'{key}' position {_preview_value(raw_position)} of "
                    f"document {document_id}: chunk positions must be integers "
                    "greater than or equal to 0."
                )
                continue
            if position not in positions:
                positions.append(position)
    if errors:
        raise RAGRetrieverEvaluationError(
            "Invalid chunk reference(s) in the decision: "
            + "; ".join(cap_errors(errors))
        )
    return _drop_empty_documents(chunks)


def _resolve_chunk_conflicts(
    requests: Dict[int, List[int]], discards: Dict[int, List[int]]
) -> None:
    """Reject chunks listed in both the request and discard fields.

    Parameters
    ----------
    requests : Dict[int, List[int]]
        Requested document positions.
    discards : Dict[int, List[int]]
        Discarded document positions.

    Returns
    -------
    None
        Nothing when there is no conflict.

    Raises
    ------
    RAGRetrieverEvaluationError
        If any chunk is both requested and discarded in the same verdict.
    """
    conflicts: List[str] = []
    for document_id in sorted(set(requests) & set(discards)):
        conflicting = []
        discarded_positions = set(discards[document_id])
        for position in requests[document_id]:
            if position in discarded_positions:
                conflicting.append(position)
        if not conflicting:
            continue
        conflicts.append(
            f"chunk position(s) {_preview_value(conflicting)} of document "
            f"{document_id} cannot be both requested and discarded in the same "
            "verdict"
        )
    if conflicts:
        raise RAGRetrieverEvaluationError(
            "Contradictory chunk operations in the decision: "
            + "; ".join(cap_errors(conflicts))
            + "."
        )


def _mapping_has_positions(mapping: Mapping[int, List[int]]) -> bool:
    """Return whether any document entry carries at least one position.

    Parameters
    ----------
    mapping : Mapping[int, List[int]]
        Document id to chunk positions.

    Returns
    -------
    bool
        ``True`` as soon as a non-empty position list is found.
    """
    found = False
    for positions in mapping.values():
        if positions:
            found = True
            break
    return found


def has_actions(
    calls: Mapping[int, int],
    requests: Mapping[int, List[int]],
    discards: Mapping[int, List[int]],
) -> bool:
    """Return whether a verdict carries at least one usable operation.

    Parameters
    ----------
    calls : Mapping[int, int]
        Retriever calls.
    requests : Mapping[int, List[int]]
        Requested chunk positions.
    discards : Mapping[int, List[int]]
        Discarded chunk positions.

    Returns
    -------
    bool
        ``True`` when at least one valid retriever call or chunk position
        remains.
    """
    if calls:
        return True
    if _mapping_has_positions(requests):
        return True
    return _mapping_has_positions(discards)


def _validate_verdict(parsed: Any, raw: Any) -> RetrievalVerdict:
    """Validate a parsed verdict against the strict evaluation contract.

    Parameters
    ----------
    parsed : Any
        The decoded verdict payload, expected to be a mapping.
    raw : Any
        Original payload (a string or a decoded mapping), echoed in error
        messages.

    Returns
    -------
    RetrievalVerdict
        The validated verdict. ``dropped_operations`` stays empty because any
        invalid operation rejects the whole verdict.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the payload is not a mapping, ``sufficient`` is missing or not a
        boolean, any retriever call or chunk entry is invalid, a chunk is both
        requested and discarded, or an insufficient verdict has no action.
        Optional narrative fields never raise.
    """
    if not isinstance(parsed, Mapping):
        raise RAGRetrieverEvaluationError(
            f"The evaluation output is not a JSON object. Preview: {_preview(raw)}"
        )

    sufficient = parsed.get(SUFFICIENT_KEY)
    if not isinstance(sufficient, bool):
        raise RAGRetrieverEvaluationError(
            f"'sufficient' must be present and a boolean. Preview: {_preview(raw)}"
        )

    calls: Dict[int, int] = {}
    if CALL_RETRIEVERS_KEY in parsed:
        calls = _validate_call_retrievers(parsed[CALL_RETRIEVERS_KEY])

    requests: Dict[int, List[int]] = {}
    if REQUEST_CHUNKS_KEY in parsed:
        requests = _validate_chunk_map(parsed[REQUEST_CHUNKS_KEY], REQUEST_CHUNKS_KEY)

    discards: Dict[int, List[int]] = {}
    if DISCARD_KEY in parsed:
        discards = _validate_chunk_map(parsed[DISCARD_KEY], DISCARD_KEY)

    _resolve_chunk_conflicts(requests, discards)
    requests = _drop_empty_documents(requests)
    discards = _drop_empty_documents(discards)

    if not sufficient and not has_actions(calls, requests, discards):
        raise RAGRetrieverEvaluationError(
            "An insufficient verdict must perform at least one action with at "
            f"least one valid operation: '{CALL_RETRIEVERS_KEY}', "
            f"'{REQUEST_CHUNKS_KEY}' or '{DISCARD_KEY}'."
            f" Preview: {_preview(raw)}"
        )

    return RetrievalVerdict(
        sufficient=sufficient,
        call_retrievers=calls,
        request_specific_chunks=requests,
        discard_specific_chunks=discards,
        message=optional_text(parsed, RAG_PROGRESS_MESSAGE_KEY),
        justification=optional_text(parsed, RAG_PROGRESS_JUSTIFICATION_KEY),
        dropped_operations=(),
    )


def parse_evaluation_output(raw: str) -> RetrievalVerdict:
    """Parse the retrieval-sufficiency verdict out of raw model output.

    Markdown fences are stripped, the substring from the first ``{`` to the last
    ``}`` is taken, and the result must be a JSON object carrying a boolean
    ``sufficient`` field. Any invalid retriever call, chunk entry or conflicting
    operation rejects the whole verdict; unknown keys are ignored.

    Parameters
    ----------
    raw : str
        Raw model output.

    Returns
    -------
    RetrievalVerdict
        The validated verdict.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the output contains no JSON object, the JSON is invalid, the parsed
        value is not a mapping, ``sufficient`` is missing or not a boolean, or
        an insufficient verdict has no valid operation left.
    """
    parsed = parse_json_object(
        raw,
        no_object_message=(
            "The evaluation model output does not contain a JSON object."
        ),
        parse_error_label="evaluation output",
    )
    return _validate_verdict(parsed, raw)


def parse_evaluation_arguments(arguments: Any) -> RetrievalVerdict:
    """Validate the arguments payload of a function call as a verdict.

    Function-calling backends return arguments either already decoded as a
    mapping or as a JSON-encoded string emitted under constrained sampling. Both
    are accepted here and validated against the same strict contract as
    :func:`parse_evaluation_output`, so the two routes cannot diverge.

    Parameters
    ----------
    arguments : Any
        The raw ``FunctionCallResult.arguments`` payload.

    Returns
    -------
    RetrievalVerdict
        The validated verdict.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the payload is a string that fails text parsing, is a mapping that
        violates the required contract, or is neither a mapping nor a string.
    """
    if isinstance(arguments, Mapping):
        return _validate_verdict(arguments, arguments)
    if isinstance(arguments, str):
        return parse_evaluation_output(arguments)
    raise RAGRetrieverEvaluationError(
        "The function-calling arguments must be a mapping or a JSON-encoded "
        f"string, got {type(arguments).__name__}. Preview: {_preview(arguments)}"
    )


def validate_call_indices(
    calls: Dict[int, int],
    retriever_count: int,
) -> Dict[int, int]:
    """Validate that every retriever index addresses a configured retriever.

    Parameters
    ----------
    calls : Dict[int, int]
        A validated ``call_retrievers`` mapping.
    retriever_count : int
        Number of retrievers the caller may address.

    Returns
    -------
    Dict[int, int]
        The same mapping, unchanged.

    Raises
    ------
    RAGRetrieverEvaluationError
        If any index is outside ``1..retriever_count``. No partial result is
        returned.
    """
    errors: List[str] = []
    for index in calls:
        if 1 <= index <= retriever_count:
            continue
        errors.append(
            f"retriever index {index} is out of range for {retriever_count} "
            "configured retriever(s); indices are 1-based"
        )
    if errors:
        raise RAGRetrieverEvaluationError(
            "Invalid retriever index in the decision: "
            + "; ".join(cap_errors(errors))
            + "."
        )
    return calls


def require_planning_calls(
    verdict: RetrievalVerdict, retriever_count: int
) -> Dict[int, int]:
    """Return the retriever calls of an ensemble planning verdict.

    The planning evaluation runs over an empty pool, so it must be insufficient
    and must request at least one valid retriever.

    Parameters
    ----------
    verdict : RetrievalVerdict
        The verdict of the planning evaluation.
    retriever_count : int
        Number of child retrievers available to the ensemble.

    Returns
    -------
    Dict[int, int]
        The valid ``call_retrievers`` mapping.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the verdict is marked sufficient, requests no retriever, or names an
        out-of-range retriever index.
    """
    if verdict.sufficient:
        raise RAGRetrieverEvaluationError(
            "An ensemble planning evaluation over an empty pool must be "
            "insufficient and request retrievers, but the verdict is marked "
            "sufficient." + _dropped_suffix(verdict)
        )
    calls = validate_call_indices(verdict.call_retrievers, retriever_count)
    if not calls:
        raise RAGRetrieverEvaluationError(
            "An insufficient ensemble planning evaluation must request at "
            f"least one valid retriever via '{CALL_RETRIEVERS_KEY}'."
            + _dropped_suffix(verdict)
        )
    return calls


def _dropped_suffix(verdict: RetrievalVerdict) -> str:
    """Return the dropped-operation suffix for an error message.

    Parameters
    ----------
    verdict : RetrievalVerdict
        Verdict whose drops are summarized.

    Returns
    -------
    str
        A leading-space sentence, or ``""`` when nothing was dropped.
    """
    if not verdict.dropped_operations:
        return ""
    return " Dropped operations: " + "; ".join(verdict.dropped_operations) + "."
