"""Per-run benchmark output layout helpers.

Each CLI execution creates one timestamped run folder under the results
directory. The folder name is the run timestamp and its layout is stable
so that a file's name tells you what it contains. The run's ``config.json``
is written before execution starts (``completed: false``) and updated when
the run finishes.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from RAG_benchmark.app.config import (
    COMPONENTS_DIR_NAME,
    CONFIG_FILENAME,
    PIPELINES_DIR_NAME,
    BenchmarkConfig,
)
from RAG_benchmark.app.store import atomic_write_json

log = logging.getLogger(__name__)


@dataclass
class RunDirectory:
    """Paths for a single benchmark run folder."""

    root: Path
    components_dir: Path
    pipelines_dir: Path
    run_id: str

    @property
    def config_path(self) -> Path:
        """Return the path to the run's ``config.json`` file."""
        return self.root / CONFIG_FILENAME


def create_run_directory(results_dir: Path, run_time: datetime) -> RunDirectory:
    """Create a new timestamped run directory under *results_dir*.

    The base name is *run_time* formatted as ``%Y%m%d_%H%M%S``. If a folder
    with that name already exists, a ``_2``, ``_3``, ... suffix is appended
    until a unique path is found. The ``components`` and ``pipelines``
    subdirectories are created eagerly.
    """
    base_name = run_time.strftime("%Y%m%d_%H%M%S")
    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = 2
    candidate = results_dir / base_name
    while True:
        try:
            os.mkdir(candidate)
            break
        except FileExistsError:
            candidate = results_dir / f"{base_name}_{suffix}"
            suffix += 1
    root = candidate
    components_dir = root / COMPONENTS_DIR_NAME
    pipelines_dir = root / PIPELINES_DIR_NAME
    components_dir.mkdir(parents=True, exist_ok=True)
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    return RunDirectory(
        root=root,
        components_dir=components_dir,
        pipelines_dir=pipelines_dir,
        run_id=root.name,
    )


def write_run_config(
    run_dir: RunDirectory,
    *,
    command: str,
    start_time: datetime,
    config: BenchmarkConfig,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write the run's ``config.json`` before the benchmarks start.

    The file records the run id, command, timestamps, the benchmark config,
    an environment snapshot and any *extra* parameters. It is written
    atomically (temp file + rename).
    """
    payload: Dict[str, Any] = {
        "run_id": run_dir.run_id,
        "command": command,
        "start_time": start_time.isoformat(),
        "end_time": None,
        "completed": False,
        "config": _config_snapshot(config),
        "environment": _environment_snapshot(),
    }
    if extra is not None:
        payload["extra"] = extra
    atomic_write_json(run_dir.config_path, payload)
    return run_dir.config_path


def update_run_config(
    run_dir: RunDirectory,
    *,
    end_time: datetime,
    completed: bool,
    summary: Optional[Dict[str, Any]] = None,
) -> Path:
    """Update the run's ``config.json`` after the benchmarks finish.

    Reads the existing file and rewrites it with ``end_time``, ``completed``
    and an optional ``summary``. If the file is missing, the path is
    returned unchanged; a malformed file is rebuilt from an empty payload
    so the final state is never lost.
    """
    if not run_dir.config_path.exists():
        return run_dir.config_path
    try:
        with open(run_dir.config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        payload: Dict[str, Any] = loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError) as exc:
        log.warning("Could not read run config %s: %s", run_dir.config_path, exc)
        payload = {}
    payload["run_id"] = payload.get("run_id", run_dir.run_id)
    payload["end_time"] = end_time.isoformat()
    payload["completed"] = completed
    if summary is not None:
        payload["summary"] = summary
    atomic_write_json(run_dir.config_path, payload)
    return run_dir.config_path


def _config_snapshot(config: BenchmarkConfig) -> Dict[str, Any]:
    """Collect the benchmark config fields relevant for a run."""
    return {
        "iterations": config.iterations,
        "messages_per_conversation": config.messages_per_conversation,
        "llm_device": config.llm_device,
        "skip_passes": config.skip_passes,
        "results_dir": str(config.results_dir),
        "data_dir": str(config.data_dir),
        "papers_dir": str(config.papers_dir),
        "deepseek_model": config.deepseek_model,
        "deepseek_base_url": config.deepseek_base_url,
        "has_openai": bool(config.openai_api_key),
        "has_deepseek": bool(config.deepseek_api_key),
    }


def _environment_snapshot() -> Dict[str, str]:
    """Snapshot the Python version and host platform."""
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
