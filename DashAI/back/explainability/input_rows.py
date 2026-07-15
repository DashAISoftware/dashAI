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


def _encode_pil_image(image: Any) -> str:
    """Encode a PIL image as a base64 PNG string.

    Parameters
    ----------
    image : PIL.Image.Image
        The image to encode.

    Returns
    -------
    str
        Base64-encoded PNG bytes.
    """
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _detect_image_columns(dataset: Any, input_columns: List[str]) -> List[str]:
    """Return the input columns that hold images.

    Image cells in a DashAIDataset expose ``to_pil``; probing the first row is
    more reliable than inspecting feature type names.

    Parameters
    ----------
    dataset : datasets.Dataset
        The selected rows.
    input_columns : List[str]
        The model input columns to consider.

    Returns
    -------
    List[str]
        The input columns whose cells are images.
    """
    if len(dataset) == 0:
        return []
    first_row = dataset[0]
    return [
        column
        for column in input_columns
        if hasattr(first_row.get(column), "to_pil")
    ]


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
    image_columns = _detect_image_columns(dataset, input_columns)

    if image_columns:
        column = image_columns[0]
        instances = []
        for index in range(len(dataset)):
            cell = dataset[index][column]
            try:
                data = _encode_pil_image(cell.to_pil())
            except Exception:
                data = ""
            instances.append(
                {"kind": "image", "data": data, "mime": "image/png"}
            )
        return {"kind": "image", "columns": [column], "instances": instances}

    frame = dataset.to_pandas()[list(input_columns)]
    instances = [
        {"kind": "tabular", "values": list(row)}
        for row in frame.values.tolist()
    ]
    return {
        "kind": "tabular",
        "columns": list(input_columns),
        "instances": instances,
    }
