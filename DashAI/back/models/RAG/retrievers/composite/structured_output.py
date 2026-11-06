"""Shared parsing helpers for structured LLM outputs.

Both the retrieval-evaluation verdict parser and the filter-selection parser
tolerate markdown fences and surrounding prose while enforcing their own strict
contracts. Keeping the shared mechanics here stops the two parsers from drifting
apart while each caller keeps its own error wording.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, List, Optional

from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.progress_utils import normalize_progress_text

#: Maximum number of characters of raw model output echoed in error messages.
PREVIEW_LIMIT = 200

#: Maximum number of individual validation errors retained in one message.
ERROR_LIMIT = 50

#: Matches opening and closing markdown code fences, with or without a language.
_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*")


def preview(raw: Any) -> str:
    """Return a short, truncated preview of raw model output.

    Parameters
    ----------
    raw : Any
        Raw model output.

    Returns
    -------
    str
        The output truncated to at most :data:`PREVIEW_LIMIT` characters, with a
        trailing ellipsis when truncation happened.
    """
    text = str(raw)
    if len(text) <= PREVIEW_LIMIT:
        return text
    return text[:PREVIEW_LIMIT] + "..."


def preview_value(value: Any) -> str:
    """Return a bounded preview of a raw mapping key or position.

    Parameters
    ----------
    value : Any
        Arbitrary decoded JSON value.

    Returns
    -------
    str
        ``repr(value)`` truncated to :data:`PREVIEW_LIMIT` characters, so a huge
        model-authored value cannot inflate a log or error message.
    """
    return preview(repr(value))


def cap_errors(errors: List[str], *, limit: int = ERROR_LIMIT) -> List[str]:
    """Bound the number of individual validation errors retained.

    Parameters
    ----------
    errors : List[str]
        Validation error messages in first-seen order.
    limit : int, optional
        Maximum number of retained messages, defaults to :data:`ERROR_LIMIT`.

    Returns
    -------
    List[str]
        At most ``limit`` messages. When the input exceeds the bound, the final
        retained entry summarizes the omitted tail.
    """
    if len(errors) <= limit:
        return list(errors)
    kept = list(errors[: max(limit - 1, 0)])
    omitted = len(errors) - len(kept)
    kept.append(f"...and {omitted} more error(s).")
    return kept


def strip_fences(raw: Any) -> str:
    """Strip markdown code fences from raw model output.

    Parameters
    ----------
    raw : Any
        Raw model output; coerced with ``str``.

    Returns
    -------
    str
        The output without fence markers and surrounding whitespace.
    """
    return _FENCE_RE.sub("", str(raw)).strip()


def extract_json_object(text: str, *, no_object_message: str) -> str:
    """Extract the substring from the first ``{`` to the last ``}``.

    Parameters
    ----------
    text : str
        Text to scan (already fence-stripped by the caller).
    no_object_message : str
        Caller-specific sentence used when no JSON object is present.

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
            f"{no_object_message} Preview: {preview(text)}"
        )
    return text[start : end + 1]


def parse_json_object(
    raw: Any,
    *,
    no_object_message: str,
    parse_error_label: str,
) -> Any:
    """Parse the JSON object embedded in raw model output.

    Parameters
    ----------
    raw : Any
        Raw model output; coerced with ``str``.
    no_object_message : str
        Caller-specific sentence used when no JSON object is present.
    parse_error_label : str
        Caller-specific noun used in the JSON parse error, for example
        ``"evaluation output"``.

    Returns
    -------
    Any
        The decoded JSON value.

    Raises
    ------
    RAGRetrieverEvaluationError
        If the output contains no JSON object or the object is invalid JSON.
    """
    candidate = extract_json_object(
        strip_fences(raw), no_object_message=no_object_message
    )
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as err:
        raise RAGRetrieverEvaluationError(
            f"Failed to parse the {parse_error_label} as JSON. Preview: {preview(raw)}"
        ) from err


def coerce_int(
    value: Any,
    minimum: int,
    *,
    allow_digit_string: bool = True,
) -> Optional[int]:
    """Coerce a decoded JSON value to a bounded integer.

    Parameters
    ----------
    value : Any
        Raw value to coerce.
    minimum : int
        Smallest accepted integer.
    allow_digit_string : bool, optional
        Whether an ASCII digit string is accepted. Chunk positions are int-only,
        while mapping keys may arrive as strings from JSON. Defaults to
        ``True``.

    Returns
    -------
    Optional[int]
        The coerced integer, or ``None`` when the value is a boolean, a
        non-integer, a non-ASCII digit string (when strings are allowed) or
        below ``minimum``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        coerced = value
    elif (
        allow_digit_string
        and isinstance(value, str)
        and value.isascii()
        and value.isdigit()
    ):
        try:
            coerced = int(value)
        except ValueError:
            return None
    else:
        return None
    if coerced < minimum:
        return None
    return coerced


def optional_text(parsed: Mapping[str, Any], key: str) -> str:
    """Read one optional narrative field leniently.

    Narrative fields are cosmetic: a missing key, ``None`` or any other
    non-string value degrades to ``""`` instead of failing the retrieval. This
    keeps model drift in an ancillary field from aborting a chat turn.

    Parameters
    ----------
    parsed : Mapping[str, Any]
        The decoded payload.
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
