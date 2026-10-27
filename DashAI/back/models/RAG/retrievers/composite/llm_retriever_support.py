"""Shared construction and cleanup helpers for LLM-backed retrievers.

The LLM-evaluated retrievers and the LLM filter retriever validate their
positive-integer budgets and required component references the same way, and
both swallow LLM close failures without hiding them. Keeping those mechanics in
one module removes the duplicated implementation while preserving each
component's error wording through ``component_label``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverCompositeValidationError,
    RAGRetrieverMissingParameterError,
)


def pop_positive_int(
    params: Dict[str, Any],
    key: str,
    *,
    component_label: str,
    default: int | None = None,
    maximum: int | None = None,
) -> int:
    """Pop a validated positive integer parameter from a params mapping.

    Parameters
    ----------
    params : Dict[str, Any]
        Construction parameters; the key is removed when present.
    key : str
        Parameter name.
    component_label : str
        Human-readable component label used in the error messages.
    default : int | None, optional
        Value used when the parameter is absent. ``None`` keeps the parameter
        required and raises instead.
    maximum : int | None, optional
        Optional inclusive upper bound.

    Returns
    -------
    int
        The validated positive integer.

    Raises
    ------
    RAGRetrieverMissingParameterError
        If the parameter is absent and no default was given.
    RAGRetrieverCompositeValidationError
        If the value is a boolean, a non-integer, below 1 or above ``maximum``.
    """
    if key not in params:
        if default is None:
            raise RAGRetrieverMissingParameterError(
                f"'{key}' is required to build an {component_label}."
            )
        value = default
    else:
        value = params.pop(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or (maximum is not None and value > maximum)
    ):
        if maximum is None:  # noqa: SIM108 - explicit block required by review
            bounds = ">= 1"
        else:
            bounds = f"between 1 and {maximum}"
        raise RAGRetrieverCompositeValidationError(
            f"'{key}' must be an integer {bounds}, got {value!r}."
        )
    return value


def pop_required(
    params: Dict[str, Any],
    key: str,
    *,
    component_label: str,
) -> Any:
    """Pop a required parameter from a params mapping without defaulting.

    Parameters
    ----------
    params : Dict[str, Any]
        Construction parameters; the key is removed when present.
    key : str
        Parameter name.
    component_label : str
        Human-readable component label used in the error message.

    Returns
    -------
    Any
        The parameter value.

    Raises
    ------
    RAGRetrieverMissingParameterError
        If the parameter is absent or ``None``.
    """
    if params.get(key) is None:
        raise RAGRetrieverMissingParameterError(
            f"'{key}' is required to build an {component_label}; no default is assumed."
        )
    return params.pop(key)


def close_llm(
    llm_model: Any,
    owner_name: str,
    label: str,
    logger: logging.Logger,
) -> None:
    """Close an LLM when it exposes a ``close`` hook, swallowing failures.

    Parameters
    ----------
    llm_model : Any
        The model to close.
    owner_name : str
        Name of the owning component, echoed in the warning.
    label : str
        Human-readable model label, for example ``"evaluation LLM"``.
    logger : logging.Logger
        Logger that receives the warning; callers inject their module logger.

    Returns
    -------
    None
        Nothing. A missing hook is a no-op and a close failure is logged rather
        than raised so cleanup never masks the retrieval failure.
    """
    close = getattr(llm_model, "close", None)
    if not callable(close):
        return
    try:
        close()
    except Exception:
        logger.warning(
            "Error closing %s's %s.",
            owner_name,
            label,
            exc_info=True,
        )
