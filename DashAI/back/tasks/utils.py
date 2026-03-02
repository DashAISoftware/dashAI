import csv
import io
import json
import logging
import zipfile
from dataclasses import dataclass, field
from typing import Optional

import filetype

log = logging.getLogger(__name__)


def get_bytes_with_type_filetype(data: bytes) -> tuple[bytes, str]:
    """Uses filetype library for lightweight detection."""
    kind = filetype.guess(data)

    if kind is None:
        # Try to detect text
        try:
            data.decode("utf-8")
            return (data, "text")
        except UnicodeDecodeError:
            return (data, "unknown")

    # filetype provides mime type
    mime = kind.mime
    if mime.startswith("image/"):
        return (data, "image")
    elif mime.startswith("audio/"):
        return (data, "audio")
    elif mime.startswith("video/"):
        return (data, "video")
    elif mime == "application/pdf":
        return (data, "pdf")
    elif mime in [
        "application/zip",
        "application/x-rar",
        "application/x-7z-compressed",
    ]:
        return (data, "archive")
    else:
        return (data, "unknown")


@dataclass
class FileMetadata:
    """Structured metadata extracted from a file's raw bytes."""

    file_type: str
    size_bytes: int
    mime_type: Optional[str] = None
    encoding: Optional[str] = None
    # tabular data (CSV, JSON arrays)
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[list[str]] = None
    # image
    width: Optional[int] = None
    height: Optional[int] = None
    color_mode: Optional[str] = None
    # archive
    archive_file_count: Optional[int] = None
    archive_filenames: Optional[list[str]] = None
    extra: dict = field(default_factory=dict)


def _extract_text_metadata(data: bytes) -> dict:
    result: dict = {}
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            result["encoding"] = enc
            result["line_count"] = text.count("\n") + 1
            break
        except UnicodeDecodeError:
            continue
    return result


def _extract_csv_metadata(data: bytes) -> dict:
    result: dict = {}
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            result["encoding"] = enc
            break
        except UnicodeDecodeError:
            continue
    else:
        return result

    try:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if rows:
            result["columns"] = rows[0]
            result["column_count"] = len(rows[0])
            result["row_count"] = max(0, len(rows) - 1)
    except csv.Error as e:
        log.debug("CSV parse error during metadata extraction: %s", e)
    return result


def _extract_json_metadata(data: bytes) -> dict:
    result: dict = {}
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            result["encoding"] = enc
            break
        except UnicodeDecodeError:
            continue
    else:
        return result

    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            result["row_count"] = len(obj)
            if obj and isinstance(obj[0], dict):
                result["columns"] = list(obj[0].keys())
                result["column_count"] = len(result["columns"])
        elif isinstance(obj, dict):
            result["columns"] = list(obj.keys())
            result["column_count"] = len(result["columns"])
    except json.JSONDecodeError as e:
        log.debug("JSON parse error during metadata extraction: %s", e)
    return result


def _extract_image_metadata(data: bytes) -> dict:
    result: dict = {}
    try:
        from PIL import Image  # noqa: PLC0415

        img = Image.open(io.BytesIO(data))
        result["width"], result["height"] = img.size
        result["color_mode"] = img.mode
    except ImportError:
        log.debug("PIL not available, skipping image dimension extraction")
    except Exception as e:
        log.debug("Image metadata extraction failed: %s", e)
    return result


def _extract_archive_metadata(data: bytes) -> dict:
    result: dict = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            result["archive_file_count"] = len(names)
            result["archive_filenames"] = names[:50]
    except zipfile.BadZipFile:
        log.debug("Not a valid ZIP for archive metadata extraction")
    except Exception as e:
        log.debug("Archive metadata extraction failed: %s", e)
    return result


_TYPE_EXTRACTORS = {
    "text": _extract_text_metadata,
    "csv": _extract_csv_metadata,
    "json": _extract_json_metadata,
    "image": _extract_image_metadata,
    "archive": _extract_archive_metadata,
}


def extract_file_metadata(
    data: bytes, file_type: Optional[str] = None
) -> FileMetadata:
    """
    Extract structured metadata from raw file bytes.

    Detects the file type if not provided, then runs the appropriate
    extractor to pull out format-specific information (dimensions for
    images, row/column counts for tabular data, file list for archives,
    encoding for text formats, etc.).

    Parameters
    ----------
    data : bytes
        Raw file content.
    file_type : str, optional
        Pre-detected file type string as returned by
        ``get_bytes_with_type_filetype``. If None, detection is run
        automatically.

    Returns
    -------
    FileMetadata
        Dataclass with the file type, size, MIME type if known, and any
        format-specific fields that could be extracted.
    """
    if file_type is None:
        _, file_type = get_bytes_with_type_filetype(data)

    kind = filetype.guess(data)
    mime_type = kind.mime if kind is not None else None

    # promote plain text to csv when the content looks tabular
    if file_type == "text":
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                sample = data[:4096].decode(enc)
                sniffer = csv.Sniffer()
                if sniffer.has_header(sample):
                    file_type = "csv"
                break
            except (UnicodeDecodeError, csv.Error):
                continue

    metadata = FileMetadata(
        file_type=file_type,
        size_bytes=len(data),
        mime_type=mime_type,
    )

    extractor = _TYPE_EXTRACTORS.get(file_type)
    if extractor is not None:
        extra = extractor(data)
        metadata.encoding = extra.pop("encoding", None)
        metadata.row_count = extra.pop("row_count", None)
        metadata.column_count = extra.pop("column_count", None)
        metadata.columns = extra.pop("columns", None)
        metadata.width = extra.pop("width", None)
        metadata.height = extra.pop("height", None)
        metadata.color_mode = extra.pop("color_mode", None)
        metadata.archive_file_count = extra.pop("archive_file_count", None)
        metadata.archive_filenames = extra.pop("archive_filenames", None)
        metadata.extra = extra

    return metadata
