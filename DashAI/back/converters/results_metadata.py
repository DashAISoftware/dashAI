"""Helpers to persist optional metadata produced by converter executions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def get_converter_results_metadata_path(
    notebook_path: str | Path, converter_id: int
) -> Path:
    """Return the JSON file path used to store converter results metadata."""

    return (
        Path(notebook_path) / "converters" / str(converter_id) / "results_metadata.json"
    )


def save_converter_results_metadata(
    notebook_path: str | Path, converter_id: int, metadata: Dict[str, Any]
) -> Path:
    """Persist JSON-serializable metadata for a converter execution."""

    metadata_path = get_converter_results_metadata_path(notebook_path, converter_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return metadata_path


def load_converter_results_metadata(
    notebook_path: str | Path, converter_id: int
) -> Dict[str, Any] | None:
    """Load metadata for a converter execution if it exists."""

    metadata_path = get_converter_results_metadata_path(notebook_path, converter_id)
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))
