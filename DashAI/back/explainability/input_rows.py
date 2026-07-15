"""Serialize the original dataset rows explained by a local explainer.

A local explainer runs over a selection of rows taken from a dataset (a split
plus the first percentage of it). The frontend shows those original rows as
the "model input" for each explained instance: the feature values for tabular
tasks, the input text for text tasks, and the original image for image tasks.

This module turns the selected rows (as they were before the model's own
preprocessing) into a JSON-serializable structure the input endpoint returns
verbatim::

    {
        "kind": "tabular" | "image" | "none",
        "columns": [<str>, ...],          # tabular only
        "instances": [                    # one entry per explained instance
            {"kind": "tabular", "values": [<Any>, ...]},
            {"kind": "image", "data": <base64 str>, "mime": <str>},
            ...
        ],
    }
"""

import base64
import io
from typing import Any, Dict, List


def _is_image_feature(feature: Any) -> bool:
    """Return whether a datasets feature holds images.

    Parameters
    ----------
    feature : Any
        A value from a datasets ``Dataset.features`` mapping.

    Returns
    -------
    bool
        True when the feature is an image feature (including DashAIImage).
    """
    return "image" in type(feature).__name__.lower()


def _image_cell_to_base64(cell: Any) -> str:
    """Encode one image cell to base64, tolerating the shapes it can take.

    A datasets image cell can arrive as a dict with a ``bytes`` key, as a
    DashAIImage exposing ``bytes``, or as a decoded PIL image.

    Parameters
    ----------
    cell : Any
        The value stored in an image column for one row.

    Returns
    -------
    str
        Base64-encoded image bytes, or an empty string when no bytes are
        available.
    """
    raw = None
    if isinstance(cell, dict):
        raw = cell.get("bytes")
    elif getattr(cell, "bytes", None) is not None:
        raw = cell.bytes
    if raw is None and hasattr(cell, "save"):
        buffer = io.BytesIO()
        cell.save(buffer, format="PNG")
        raw = buffer.getvalue()
    if raw is None:
        return ""
    return base64.b64encode(bytes(raw)).decode("ascii")


def serialize_local_input_rows(
    dataset: Any, input_columns: List[str]
) -> Dict[str, Any]:
    """Serialize the explained rows of a local explainer for the frontend.

    Parameters
    ----------
    dataset : datasets.Dataset
        The selected rows as they were before the model's preprocessing, in
        explanation order (row ``i`` is explained instance ``i``).
    input_columns : List[str]
        The model input columns to include.

    Returns
    -------
    Dict[str, Any]
        A JSON-serializable structure as documented in the module docstring.
        Image tasks use the first image input column; all other tasks are
        rendered as a table of feature values (text columns included).
    """
    features = getattr(dataset, "features", {}) or {}
    image_columns = [
        column for column in input_columns if _is_image_feature(features.get(column))
    ]

    if image_columns:
        column = image_columns[0]
        instances = [
            {
                "kind": "image",
                "data": _image_cell_to_base64(row[column]),
                "mime": "image/png",
            }
            for row in dataset
        ]
        return {"kind": "image", "columns": [column], "instances": instances}

    frame = dataset.to_pandas()[list(input_columns)]
    instances = [
        {"kind": "tabular", "values": list(row)} for row in frame.values.tolist()
    ]
    return {
        "kind": "tabular",
        "columns": list(input_columns),
        "instances": instances,
    }
