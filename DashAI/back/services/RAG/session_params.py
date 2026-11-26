"""Whitelist filtering of a RAG session's stored parameters.

A session stores whatever its client sent, so the parameters can carry keys the
pipeline does not understand. Each job keeps only the keys its own stage uses.
"""

from collections.abc import Collection, Mapping
from typing import Any


def filter_pipeline_params(
    raw_params: Mapping[str, Any], allowed_keys: Collection[str]
) -> dict[str, Any]:
    """Keep only the session parameters that a pipeline stage accepts.

    Parameters
    ----------
    raw_params : Mapping[str, Any]
        The session parameters, with prompts already materialized.
    allowed_keys : Collection[str]
        The key names the stage accepts. Each caller passes its own set: the
        chat job also admits the optional query transformation stage, while the
        index job does not.

    Returns
    -------
    dict[str, Any]
        A new mapping holding the entries of *raw_params* whose keys are allowed.
    """
    allowed = frozenset(allowed_keys)
    filtered: dict[str, Any] = {}
    for key, value in raw_params.items():
        if key in allowed:
            filtered[key] = value
    return filtered
