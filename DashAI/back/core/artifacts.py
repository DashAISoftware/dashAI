"""Typed render artifacts shared by explainers and explorers.

An artifact is the unit of renderable output that a component (an explainer's
``plot`` method, an explorer's ``get_results`` method) hands to the frontend.
Every artifact serializes to the wire format::

    {"type": <str>, "payload": <Any>, "title": <Optional[str]>}

Supported types:

- ``"plotly"``: payload is a JSON string produced by ``plotly.io.to_json``.
- ``"table"``: payload is ``{"columns": List[str], "rows": List[List[Any]],
  "highlight": List[{"row": int, "column": int}]}``.
- ``"text"``: payload is a plain string rendered as preformatted text.
- ``"image"``: payload is ``{"data": <base64 str>, "mime": <str>}``.

Components created before this module returned other shapes: explainers
returned lists of plotly JSON strings, explorers returned a single
``{"data", "type", "config"}`` dict. :func:`normalize_artifacts` upgrades
both legacy shapes, so old pickled explanations, old saved explorations and
legacy plugin components keep working.
"""

import base64
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

_IMAGE_MAGIC_MIMES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)


def _detect_mime(data: bytes) -> str:
    """Guess the MIME type of raw image bytes from their magic numbers.

    Parameters
    ----------
    data : bytes
        Raw image bytes.

    Returns
    -------
    str
        The detected MIME type, or ``"image/png"`` when unknown.
    """
    for magic, mime in _IMAGE_MAGIC_MIMES:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


class Artifact(BaseModel):
    """Base class for typed render artifacts.

    Attributes
    ----------
    type : str
        Discriminator naming the artifact kind; fixed per subclass.
    title : Optional[str]
        Human readable title shown above the rendered artifact.
    """

    type: str
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the artifact to its wire format.

        Returns
        -------
        Dict[str, Any]
            ``{"type", "payload", "title"}`` with a JSON-serializable payload.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Deserialize a wire format dict into the matching artifact subclass.

        Parameters
        ----------
        data : Dict[str, Any]
            A dict with ``type``, ``payload`` and optionally ``title``.

        Returns
        -------
        Artifact
            An instance of the subclass matching ``data["type"]``.

        Raises
        ------
        ValueError
            If the type is unknown or the payload is malformed.
        """
        try:
            return _ANY_ARTIFACT_ADAPTER.validate_python(data)
        except ValidationError as error:
            raise ValueError(f"Invalid artifact dict: {error}") from error


class PlotlyArtifact(Artifact):
    """Artifact holding a plotly figure serialized as JSON.

    Attributes
    ----------
    payload : str
        JSON string produced by ``plotly.io.to_json``. A live plotly
        ``Figure`` may be passed instead; it is serialized on validation.
    """

    type: Literal["plotly"] = "plotly"
    payload: str

    @field_validator("payload", mode="before")
    @classmethod
    def _serialize_figure(cls, value: Any) -> Any:
        if not isinstance(value, str) and hasattr(value, "to_plotly_json"):
            import plotly.io as pio

            return pio.to_json(value)
        return value


class TableCell(BaseModel):
    """Reference to a single table cell, 0-indexed relative to ``rows``.

    Attributes
    ----------
    row : int
        Row index of the cell.
    column : int
        Column index of the cell.
    """

    row: int = Field(ge=0)
    column: int = Field(ge=0)


class TablePayload(BaseModel):
    """Payload of a table artifact.

    Attributes
    ----------
    columns : List[str]
        Column headers.
    rows : List[List[Any]]
        Table rows; every row must have ``len(columns)`` cells.
    highlight : List[TableCell]
        Cells to emphasise when rendered.
    """

    columns: List[str]
    rows: List[List[Any]]
    highlight: List[TableCell] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_shape(self) -> "TablePayload":
        for i, row in enumerate(self.rows):
            if len(row) != len(self.columns):
                raise ValueError(
                    f"Row {i} has {len(row)} cells, expected {len(self.columns)}."
                )
        for cell in self.highlight:
            if cell.row >= len(self.rows) or cell.column >= len(self.columns):
                raise ValueError(
                    f"Highlight cell ({cell.row}, {cell.column}) is out of bounds."
                )
        return self


class TableArtifact(Artifact):
    """Artifact holding tabular data with optional highlighted cells.

    Attributes
    ----------
    payload : TablePayload
        Columns, rows and highlighted cells.
    """

    type: Literal["table"] = "table"
    payload: TablePayload


class TextArtifact(Artifact):
    """Artifact holding plain text rendered preformatted.

    Attributes
    ----------
    payload : str
        Text content; newlines are preserved when rendered.
    """

    type: Literal["text"] = "text"
    payload: str


class ImagePayload(BaseModel):
    """Payload of an image artifact.

    Attributes
    ----------
    data : str
        Base64-encoded image bytes. Raw ``bytes`` may be passed instead;
        they are encoded on validation.
    mime : str
        MIME type of the encoded image.
    """

    data: str
    mime: str = "image/png"

    @field_validator("data", mode="before")
    @classmethod
    def _encode_bytes(cls, value: Any) -> Any:
        if isinstance(value, (bytes, bytearray)):
            return base64.b64encode(bytes(value)).decode("ascii")
        if isinstance(value, str):
            try:
                base64.b64decode(value, validate=True)
            except Exception as error:
                raise ValueError("data is not valid base64.") from error
        return value


class ImageArtifact(Artifact):
    """Artifact holding a base64-encoded image.

    Attributes
    ----------
    payload : ImagePayload
        Base64 data and MIME type.
    """

    type: Literal["image"] = "image"
    payload: ImagePayload

    @classmethod
    def from_dashai_image(
        cls, image: Any, title: Optional[str] = None
    ) -> "ImageArtifact":
        """Build an image artifact from a dataset :class:`DashAIImage` value.

        Parameters
        ----------
        image : DashAIImage
            A dataset image instance carrying raw bytes.
        title : Optional[str]
            Human readable title shown above the artifact.

        Returns
        -------
        ImageArtifact
            The artifact wrapping the image bytes.

        Raises
        ------
        ValueError
            If the image has no bytes available.
        """
        if getattr(image, "bytes", None) is None:
            raise ValueError("DashAIImage has no bytes available.")
        return cls(
            payload=ImagePayload(data=image.bytes, mime=_detect_mime(image.bytes)),
            title=title,
        )


AnyArtifact = Annotated[
    Union[PlotlyArtifact, TableArtifact, TextArtifact, ImageArtifact],
    Field(discriminator="type"),
]

_ANY_ARTIFACT_ADAPTER: TypeAdapter = TypeAdapter(AnyArtifact)


def _legacy_explorer_artifact(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy explorer result dict into an artifact dict.

    Parameters
    ----------
    item : Dict[str, Any]
        A dict with the old explorer contract ``{"data", "type", "config"}``.

    Returns
    -------
    Dict[str, Any]
        The equivalent artifact dict; unknown legacy types degrade to a
        text artifact.
    """
    legacy_type = item.get("type")
    data = item.get("data")
    if legacy_type == "plotly_json" and isinstance(data, str):
        return PlotlyArtifact(payload=data).to_dict()
    if legacy_type == "tabular" and isinstance(data, dict):
        columns = ["index", *data.keys()]
        index_keys: List[Any] = []
        for column_values in data.values():
            if isinstance(column_values, dict):
                for key in column_values:
                    if key not in index_keys:
                        index_keys.append(key)
        rows = [
            [key, *(data[column].get(key) for column in data)] for key in index_keys
        ]
        return TableArtifact(payload=TablePayload(columns=columns, rows=rows)).to_dict()
    if legacy_type == "image_base64" and isinstance(data, str):
        return ImageArtifact(payload=ImagePayload(data=data)).to_dict()
    return TextArtifact(payload=str(data)).to_dict()


def normalize_artifacts(items: Any) -> List[Dict[str, Any]]:
    """Coerce any component output into a list of artifact wire dicts.

    Handles current values (``Artifact`` instances or artifact dicts) and
    legacy shapes: plain plotly JSON strings from old explainers, and
    ``{"data", "type", "config"}`` dicts from old explorers. Anything else
    is stringified into a text artifact so the frontend never receives an
    unrenderable value.

    Parameters
    ----------
    items : Any
        The value returned by an explainer ``plot`` method, an explorer
        ``get_results`` method, or loaded from a persisted result file.

    Returns
    -------
    List[Dict[str, Any]]
        A list of artifact dicts in wire format.
    """
    if items is None:
        return []
    if isinstance(items, (str, dict, Artifact)):
        items = [items]

    artifacts: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, Artifact):
            artifacts.append(item.to_dict())
        elif isinstance(item, str):
            artifacts.append(PlotlyArtifact(payload=item).to_dict())
        elif isinstance(item, dict) and "type" in item and "payload" in item:
            artifacts.append({"title": None, **item})
        elif isinstance(item, dict) and "type" in item and "data" in item:
            artifacts.append(_legacy_explorer_artifact(item))
        else:
            artifacts.append(TextArtifact(payload=str(item)).to_dict())
    return artifacts
