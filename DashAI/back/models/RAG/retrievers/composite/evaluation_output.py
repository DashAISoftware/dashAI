"""Fence-tolerant, per-operation-tolerant parser for the evaluation contract.

The LLM-evaluated retrievers ask their language model for a single JSON verdict
that judges whether the retrieved pool is sufficient and, when it is not, how to
proceed. In practice models wrap that object in prose or markdown fences and
occasionally emit a malformed operation alongside valid ones. This parser
tolerates the wrapping and drops invalid operations individually: a bad retriever
entry or chunk position never discards the rest of the verdict.

Contract
--------
``{"sufficient": true}`` — the pool answers the query.

An insufficient verdict carries any combination of:

* ``call_retrievers`` — ``{<1-based retriever index>: <top_k>}``;
* ``request_specific_chunks`` — ``{<document id>: [<chunk positions>]}``;
* ``discard_specific_chunks`` — ``{<document id>: [<chunk positions>]}``.

Requested and discarded chunks persist across rounds and can override each other
(the last action wins). A chunk listed in both fields of one verdict is dropped
from both because the two actions are mutually exclusive. An insufficient
verdict that has no valid action left after dropping is rejected: it cannot make
progress.

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

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.progress_utils import normalize_progress_text
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
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

logger = logging.getLogger(__name__)

#: Maximum number of characters of raw model output echoed in error messages.
_PREVIEW_LIMIT = 200

#: Maximum number of dropped-operation messages retained in a verdict/trace.
_MAX_DROPPED_OPERATIONS = 50

#: Recognizes the synthetic summary produced when a drop list is capped.
_DROPPED_SUMMARY_RE = re.compile(r"^Dropped (\d+) more invalid operation\(s\)\.$")

#: Matches opening and closing markdown code fences, with or without a language.
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*")


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
        Short, JSON-serializable descriptions of the operations dropped while
        parsing or finalizing the verdict. Empty when everything was valid.
    """

    sufficient: bool
    call_retrievers: Dict[int, int] = field(default_factory=dict)
    request_specific_chunks: Dict[int, List[int]] = field(default_factory=dict)
    discard_specific_chunks: Dict[int, List[int]] = field(default_factory=dict)
    message: str = ""
    justification: str = ""
    dropped_operations: Tuple[str, ...] = ()


def _preview(raw: Any) -> str:
    """Return a short, truncated preview of the raw model output.

    Parameters
    ----------
    raw : Any
        Raw model output.

    Returns
    -------
    str
        The output truncated to at most ``_PREVIEW_LIMIT`` characters, with a
        trailing ellipsis when truncation happened.
    """
    text = str(raw)
    if len(text) <= _PREVIEW_LIMIT:
        return text
    return text[:_PREVIEW_LIMIT] + "..."


def _preview_value(value: Any) -> str:
    """Return a bounded preview of a raw mapping key or position.

    Parameters
    ----------
    value : Any
        Arbitrary decoded JSON value.

    Returns
    -------
    str
        ``repr(value)`` truncated to ``_PREVIEW_LIMIT`` characters, so a huge
        model-authored key/position cannot inflate the log or error message.
    """
    return _preview(repr(value))


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


def _extract_json_object(text: str) -> str:
    """Extract the substring from the first ``{`` to the last ``}``.

    Parameters
    ----------
    text : str
        Text to scan.

    Returns
    -------
    str
        The candidate JSON object.

    Raises
    ------
    RAGRetrieverEvaluationError
        If no braces are present or their order is inverted.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RAGRetrieverEvaluationError(
            "The evaluation model output does not contain a JSON object. "
            f"Preview: {_preview(text)}"
        )
    return text[start : end + 1]


def _coerce_mapping_key(value: Any, minimum: int) -> Optional[int]:
    """Coerce a mapping key to an integer honouring the contract bounds.

    Parameters
    ----------
    value : Any
        Raw mapping key (an integer or a digit string).
    minimum : int
        Smallest accepted value.

    Returns
    -------
    Optional[int]
        The coerced key, or ``None`` when it is a non-digit value, a boolean or
        below ``minimum``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        coerced = value
    elif isinstance(value, str) and value.isdigit():
        coerced = int(value)
    else:
        return None
    if coerced < minimum:
        return None
    return coerced


def _coerce_position(value: Any, minimum: int) -> Optional[int]:
    """Coerce a chunk position to an integer honouring the contract bounds.

    Parameters
    ----------
    value : Any
        Raw chunk position.
    minimum : int
        Smallest accepted value.

    Returns
    -------
    Optional[int]
        The position, or ``None`` when it is a boolean, a non-integer or below
        ``minimum``.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return None
    return value


def _validate_call_retrievers(
    value: Any,
) -> Tuple[Dict[int, int], List[str]]:
    """Validate the ``call_retrievers`` mapping tolerantly.

    Parameters
    ----------
    value : Any
        Raw ``call_retrievers`` value from the parsed verdict.

    Returns
    -------
    Tuple[Dict[int, int], List[str]]
        1-based retriever index to requested chunk count, plus one message per
        dropped operation. A non-mapping drops the whole field; an invalid
        entry is dropped individually; a later duplicate index is dropped.
    """
    if not isinstance(value, Mapping):
        return {}, [
            f"Dropped '{CALL_RETRIEVERS_KEY}': expected a mapping of retriever "
            f"index to top_k, got {type(value).__name__}."
        ]
    calls: Dict[int, int] = {}
    seen: set[int] = set()
    drops: List[str] = []
    for raw_index, raw_top_k in value.items():
        index = _coerce_mapping_key(raw_index, 1)
        if index is None:
            drops.append(
                f"Dropped '{CALL_RETRIEVERS_KEY}' entry "
                f"{_preview_value(raw_index)}: retriever index must be an "
                "integer greater than or equal to 1."
            )
            continue
        if index in seen:
            drops.append(
                f"Dropped '{CALL_RETRIEVERS_KEY}' duplicate entry for retriever "
                f"index {index}; the first valid entry is kept."
            )
            continue
        top_k = _coerce_position(raw_top_k, 1)
        if top_k is None:
            drops.append(
                f"Dropped '{CALL_RETRIEVERS_KEY}' entry {index}: top_k must be an "
                "integer greater than or equal to 1."
            )
            continue
        seen.add(index)
        calls[index] = top_k
    return calls, drops


def _validate_chunk_map(value: Any, key: str) -> Tuple[Dict[int, List[int]], List[str]]:
    """Validate one document-to-positions mapping tolerantly.

    Parameters
    ----------
    value : Any
        Raw mapping from the parsed verdict.
    key : str
        Canonical contract field name, echoed in drop messages.

    Returns
    -------
    Tuple[Dict[int, List[int]], List[str]]
        Document id to chunk positions (deduplicated in first-seen order, empty
        document entries omitted), plus one message per dropped operation. A
        non-mapping drops the whole field; bad document entries and positions
        are dropped individually; duplicate coerced ids union their positions.
    """
    if not isinstance(value, Mapping):
        return {}, [
            f"Dropped '{key}': expected a mapping of document id to chunk "
            f"positions, got {type(value).__name__}."
        ]
    chunks: Dict[int, List[int]] = {}
    drops: List[str] = []
    for raw_document_id, raw_positions in value.items():
        document_id = _coerce_mapping_key(raw_document_id, 0)
        if document_id is None:
            drops.append(
                f"Dropped '{key}' entry {_preview_value(raw_document_id)}: "
                "document id must be an integer greater than or equal to 0."
            )
            continue
        if not isinstance(raw_positions, list):
            drops.append(
                f"Dropped '{key}' document {document_id}: positions must be a "
                f"list, got {type(raw_positions).__name__}."
            )
            continue
        positions = chunks.setdefault(document_id, [])
        for raw_position in raw_positions:
            position = _coerce_position(raw_position, 0)
            if position is None:
                drops.append(
                    f"Dropped '{key}' position {_preview_value(raw_position)} of "
                    f"document {document_id}: chunk positions must be integers "
                    "greater than or equal to 0."
                )
                continue
            if position not in positions:
                positions.append(position)
    return _drop_empty_documents(chunks), drops


def _resolve_chunk_conflicts(
    requests: Dict[int, List[int]], discards: Dict[int, List[int]]
) -> List[str]:
    """Remove chunks listed in both request and discard fields.

    Requesting and discarding the same chunk in one verdict is contradictory, so
    the chunk is removed from both fields while every other position is kept.

    Parameters
    ----------
    requests : Dict[int, List[int]]
        Requested document positions (mutated in place).
    discards : Dict[int, List[int]]
        Discarded document positions (mutated in place).

    Returns
    -------
    List[str]
        One drop message per document that had a conflicting position.
    """
    drops: List[str] = []
    for document_id in sorted(set(requests) & set(discards)):
        conflicting: List[int] = []
        discarded_positions = discards[document_id]
        for position in requests[document_id]:
            if position in discarded_positions:
                conflicting.append(position)
        if not conflicting:
            continue
        conflicting_set = set(conflicting)
        remaining_requests: List[int] = []
        for position in requests[document_id]:
            if position not in conflicting_set:
                remaining_requests.append(position)
        remaining_discards: List[int] = []
        for position in discards[document_id]:
            if position not in conflicting_set:
                remaining_discards.append(position)
        requests[document_id] = remaining_requests
        discards[document_id] = remaining_discards
        drops.append(
            f"Dropped chunk position(s) {_preview_value(conflicting)} of "
            f"document {document_id} from both '{REQUEST_CHUNKS_KEY}' and "
            f"'{DISCARD_KEY}': they cannot be both requested and discarded in "
            "the same verdict."
        )
    return drops


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


def _validate_optional_text(parsed: Mapping[str, Any], key: str) -> str:
    """Read one optional narrative field leniently.

    Narrative fields are cosmetic: a missing key, ``None`` or any other
    non-string value degrades to ``""`` instead of failing the retrieval. This
    keeps model drift in an ancillary field from aborting a chat turn.

    Parameters
    ----------
    parsed : Mapping[str, Any]
        The decoded verdict payload.
    key : str
        Contract field name (``message`` or ``justification``).

    Returns
    -------
    str
        The normalized text (whitespace collapsed and capped), or ``""`` when
        the key is absent or not a string.
    """
    value = parsed.get(key)
    if not isinstance(value, str):
        return ""
    return normalize_progress_text(value)


def _validate_verdict(parsed: Any, raw: Any) -> RetrievalVerdict:
    """Validate a parsed verdict against the tolerant evaluation contract.

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
        The validated verdict, carrying the operations that had to be dropped.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the payload is not a mapping, ``sufficient`` is missing or not a
        boolean, or an insufficient verdict has no valid operation left after
        the invalid ones were dropped. Optional narrative fields never raise.
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

    drops: List[str] = []
    calls: Dict[int, int] = {}
    if CALL_RETRIEVERS_KEY in parsed:
        calls, call_drops = _validate_call_retrievers(parsed[CALL_RETRIEVERS_KEY])
        drops.extend(call_drops)

    requests: Dict[int, List[int]] = {}
    if REQUEST_CHUNKS_KEY in parsed:
        requests, request_drops = _validate_chunk_map(
            parsed[REQUEST_CHUNKS_KEY], REQUEST_CHUNKS_KEY
        )
        drops.extend(request_drops)

    discards: Dict[int, List[int]] = {}
    if DISCARD_KEY in parsed:
        discards, discard_drops = _validate_chunk_map(parsed[DISCARD_KEY], DISCARD_KEY)
        drops.extend(discard_drops)

    drops.extend(_resolve_chunk_conflicts(requests, discards))
    requests = _drop_empty_documents(requests)
    discards = _drop_empty_documents(discards)
    dropped_count = len(drops)
    drops = cap_dropped_operations(drops)

    if drops:
        logger.warning(
            "Dropped %d invalid evaluation operation(s): %s",
            dropped_count,
            "; ".join(drops),
        )

    if not sufficient and not has_actions(calls, requests, discards):
        detail = ""
        if drops:
            detail = f" Dropped operations: {'; '.join(drops)}."
        raise RAGRetrieverEvaluationError(
            "An insufficient verdict must perform at least one action with at "
            f"least one valid operation: '{CALL_RETRIEVERS_KEY}', "
            f"'{REQUEST_CHUNKS_KEY}' or '{DISCARD_KEY}'."
            + detail
            + f" Preview: {_preview(raw)}"
        )

    return RetrievalVerdict(
        sufficient=sufficient,
        call_retrievers=calls,
        request_specific_chunks=requests,
        discard_specific_chunks=discards,
        message=_validate_optional_text(parsed, RAG_PROGRESS_MESSAGE_KEY),
        justification=_validate_optional_text(parsed, RAG_PROGRESS_JUSTIFICATION_KEY),
        dropped_operations=tuple(drops),
    )


def parse_evaluation_output(raw: str) -> RetrievalVerdict:
    """Parse the retrieval-sufficiency verdict out of raw model output.

    Markdown fences are stripped, the substring from the first ``{`` to the last
    ``}`` is taken, and the result must be a JSON object carrying a boolean
    ``sufficient`` field. Invalid operations inside the action maps are dropped
    individually; unknown keys are ignored.

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
    text = _FENCE_RE.sub("", str(raw)).strip()
    candidate = _extract_json_object(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as err:
        raise RAGRetrieverEvaluationError(
            f"Failed to parse the evaluation output as JSON. Preview: {_preview(raw)}"
        ) from err
    return _validate_verdict(parsed, raw)


def parse_evaluation_arguments(arguments: Any) -> RetrievalVerdict:
    """Validate the arguments payload of a function call as a verdict.

    Function-calling backends return arguments either already decoded as a
    mapping or as a JSON-encoded string emitted under constrained sampling. Both
    are accepted here; the payload is validated against the same tolerant
    contract as :func:`parse_evaluation_output`, so the two routes cannot
    diverge.

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
    dropped: Optional[List[str]] = None,
) -> Dict[int, int]:
    """Drop retriever indices that address no configured retriever.

    Parameters
    ----------
    calls : Dict[int, int]
        A validated ``call_retrievers`` mapping.
    retriever_count : int
        Number of retrievers the caller may address.
    dropped : Optional[List[str]]
        When provided, clear drop messages are appended here; otherwise each one
        is logged. The function never raises for an out-of-range index.

    Returns
    -------
    Dict[int, int]
        The subset of ``calls`` whose indices fall inside
        ``1..retriever_count``.
    """
    valid: Dict[int, int] = {}
    for index, top_k in calls.items():
        if 1 <= index <= retriever_count:
            valid[index] = top_k
            continue
        message = (
            f"Dropped '{CALL_RETRIEVERS_KEY}' entry {index}: retriever index is "
            f"out of range for {retriever_count} configured retriever(s); "
            "indices are 1-based."
        )
        if dropped is None:
            logger.warning(message)
        else:
            dropped.append(message)
    return valid


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
        If the verdict is marked sufficient, or no valid retriever call remains
        after dropping out-of-range indices.
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
