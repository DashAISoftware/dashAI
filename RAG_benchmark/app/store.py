"""Atomic JSON stores and CSV appending helpers for incremental output.

Every benchmark run writes ``configs.json`` and ``io.json`` alongside a
``results.csv``. The JSON stores persist their whole dict on every ``set``
so a crash mid-run never loses already-completed executions.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

log = logging.getLogger(__name__)

#: File names shared by component and pipeline results folders.
RESULTS_CSV_FILENAME = "results.csv"
CONFIGS_JSON_FILENAME = "configs.json"
IO_JSON_FILENAME = "io.json"

#: Times the atomic rename is retried before giving up. On Windows another
#: process (the DAST/antivirus scanner, a cloud-sync client or an editor
#: tailing the results) can briefly hold the destination file open, and the
#: replace then fails with a sharing violation. A short retry rides that out
#: instead of aborting the whole benchmark category.
REPLACE_ATTEMPTS = 5
#: Base delay between replace attempts; grows linearly per attempt.
REPLACE_DELAY_SECONDS = 0.1

#: Windows error codes for "access denied" and "sharing violation", the two
#: transient failures a rename hits when the destination is briefly open.
_WINDOWS_TRANSIENT_WINERRORS = {5, 32}


def _is_transient_replace_error(exc: OSError) -> bool:
    """Return whether *exc* is a transient file-lock failure worth retrying.

    Parameters
    ----------
    exc : OSError
        The error raised by ``Path.replace``.

    Returns
    -------
    bool
        ``True`` for a ``PermissionError`` or a Windows sharing violation,
        ``False`` for anything that would fail again (missing file, bad path).
    """
    if isinstance(exc, PermissionError):
        return True
    return getattr(exc, "winerror", None) in _WINDOWS_TRANSIENT_WINERRORS


def _replace_with_retry(tmp_path: Path, path: Path) -> None:
    """Rename *tmp_path* onto *path*, retrying a transient Windows lock.

    Parameters
    ----------
    tmp_path : Path
        The fully written temporary file.
    path : Path
        The destination file, which may be briefly open elsewhere.

    Raises
    ------
    OSError
        If the rename keeps failing after :data:`REPLACE_ATTEMPTS` tries.
    """
    for attempt in range(1, REPLACE_ATTEMPTS + 1):
        try:
            tmp_path.replace(path)
            return
        except OSError as exc:
            if attempt == REPLACE_ATTEMPTS or not _is_transient_replace_error(exc):
                raise
            log.warning(
                "Could not replace %s (attempt %d/%d): %s; retrying",
                path,
                attempt,
                REPLACE_ATTEMPTS,
                exc,
            )
            time.sleep(REPLACE_DELAY_SECONDS * attempt)


def atomic_write_json(path: Path, payload: Any) -> None:
    """Write *payload* to *path* via a temp file and an atomic rename.

    The temp file is flushed and fsynced before the rename so a power loss
    never leaves a truncated JSON file behind.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    _replace_with_retry(tmp_path, path)


def csv_single_line(value: str) -> str:
    """Replace newline characters with a space so CSV cells stay on one line."""
    return value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")


class JsonStore:
    """Persist a JSON dict atomically, keyed by string ids.

    The store keeps an in-memory dict that is fully rewritten to *path*
    on every :meth:`set` call (write to a temp file, then rename), so the
    file on disk always reflects the latest state even if the process dies
    right after a write.

    Parameters
    ----------
    path : Path
        Destination JSON file. Its parent directory must exist.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: Dict[str, Any] = self.load()

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* and persist the whole dict atomically."""
        self._data[key] = value
        atomic_write_json(self.path, self._data)

    def load(self) -> Dict[str, Any]:
        """Read the JSON file into a dict, or return an empty dict if absent.

        An unreadable or malformed file is logged and treated as empty so a
        corrupted store never aborts a run; the next :meth:`set` rewrites it.
        """
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
            log.warning("JSON store %s is not a dict; treating as empty", self.path)
        except (OSError, ValueError) as exc:
            log.warning("Could not read JSON store %s: %s", self.path, exc)
        return {}


def append_csv_row(csv_path: Path, fieldnames: List[str], row: Dict[str, Any]) -> None:
    """Append a row to *csv_path*, creating the header if the file is new.

    Parameters
    ----------
    csv_path : Path
        Destination CSV file. Its parent directory must exist.
    fieldnames : list[str]
        Column names, used for the header and to order *row*.
    row : dict[str, Any]
        Values for one CSV row; keys must match *fieldnames*.
    """
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
