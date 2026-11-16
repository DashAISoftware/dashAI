from __future__ import annotations

import csv
import gc
import importlib
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from RAG_benchmark.app.store import (
    CONFIGS_JSON_FILENAME,
    IO_JSON_FILENAME,
    RESULTS_CSV_FILENAME,
    JsonStore,
    append_csv_row,
    csv_single_line,
)

#: All statuses a component run can record.
_STATUS_VALUES = {"passed", "failed", "incorrect", "skipped"}


def load_component_class(
    component_map: dict[str, tuple[str, str]], component: str
) -> type:
    """Import and return the class behind a ``(module_path, class_name)`` map entry.

    Parameters
    ----------
    component_map : dict[str, tuple[str, str]]
        Map from component name to its ``(module_path, class_name)`` pair.
    component : str
        The component name to resolve.

    Returns
    -------
    type
        The imported component class.
    """
    module_path, class_name = component_map[component]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


#: Column names of the component-level ``results.csv`` file.
COMPONENT_CSV_COLUMNS: List[str] = [
    "id",
    "timestamp",
    "component_type",
    "component_class",
    "model_name",
    "config_name",
    "status",
    "time_seconds",
    "first_load_time",
    "error_message",
]


@dataclass
class BenchmarkResult:
    """A single benchmark test result."""

    component_type: str
    component_class: str
    model_name: str
    config_name: str
    params: Dict[str, Any]
    status: str  # "passed", "failed", "skipped"
    time_seconds: float
    first_load_time: float
    error_message: str  # "" if passed, str if failed
    timestamp: str  # ISO format timestamp


class BenchmarkLogger:
    """Logs component benchmark executions incrementally to a run folder.

    Each logged execution writes one row to ``results.csv`` and sets the
    matching keys in ``configs.json`` and ``io.json``. Every row shares the
    same ``id`` across the three files so a result can be joined back to its
    full config and inputs/outputs.

    Parameters
    ----------
    output_dir : Path
        Directory where the files are written (created if missing).
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / RESULTS_CSV_FILENAME
        self.configs = JsonStore(self.output_dir / CONFIGS_JSON_FILENAME)
        self.io = JsonStore(self.output_dir / IO_JSON_FILENAME)
        self.results: list[BenchmarkResult] = []
        self.result_ids: list[str] = []
        self._counter = 0

    def log(
        self,
        result: BenchmarkResult,
        config: Dict[str, Any],
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> str:
        """Record one execution, persisting CSV, config and io immediately.

        The JSON stores are written before the CSV row so that, on a crash
        between writes, the full config and inputs/outputs are recoverable
        even if the flat CSV row is missing.

        Parameters
        ----------
        result : BenchmarkResult
            The flat result record for this execution.
        config : dict[str, Any]
            The full component config dict (with nested params).
        inputs : dict[str, Any]
            Inputs captured for the execution.
        outputs : dict[str, Any]
            Outputs captured for the execution.

        Returns
        -------
        str
            The zero-padded ``id`` shared by the CSV row, ``configs.json``
            and ``io.json`` entries.
        """
        self._counter += 1
        result_id = f"{self._counter:04d}"
        self.results.append(result)
        self.result_ids.append(result_id)
        self.configs.set(result_id, config)
        self.io.set(result_id, {"inputs": inputs, "outputs": outputs})
        append_csv_row(
            self.csv_path,
            COMPONENT_CSV_COLUMNS,
            {
                "id": result_id,
                "timestamp": result.timestamp,
                "component_type": result.component_type,
                "component_class": result.component_class,
                "model_name": result.model_name,
                "config_name": result.config_name,
                "status": result.status,
                "time_seconds": f"{result.time_seconds:.6f}",
                "first_load_time": f"{result.first_load_time:.6f}",
                "error_message": csv_single_line(result.error_message),
            },
        )
        return result_id

    def summary(self) -> str:
        """Return a human-readable summary string."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        incorrect = sum(1 for r in self.results if r.status == "incorrect")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        lines = [
            f"\n{'=' * 60}",
            "  BENCHMARK SUMMARY",
            f"{'=' * 60}",
            f"  Total:     {total}",
            f"  Passed:    {passed}  (ejecucion correcta + respuesta correcta)",
            f"  Incorrect: {incorrect}  (ejecucion correcta + respuesta incorrecta)",
            f"  Failed:    {failed}  (error de ejecucion)",
            f"  Skipped:   {skipped}",
            f"  CSV:       {self.csv_path}",
            f"  Configs:   {self.configs.path}",
            f"  IO:        {self.io.path}",
            f"{'=' * 60}",
        ]
        if failed > 0:
            lines.append("\n  FAILURES (errores de ejecucion):")
            for r in self.results:
                if r.status == "failed":
                    lines.append(
                        f"    FAIL {r.component_class}[{r.config_name}]: "
                        f"{r.error_message[:100]}"
                    )
        if incorrect > 0:
            lines.append("\n  INCORRECT (ejecucion OK, respuesta incorrecta):")
            for r in self.results:
                if r.status == "incorrect":
                    lines.append(
                        f"    WARN {r.component_class}[{r.config_name}]: "
                        f"{r.error_message[:100]}"
                    )
        return "\n".join(lines)


class Timer:
    """Context manager to measure elapsed time."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start


def ensure_component_store() -> None:
    """Register the default DashAI config service so downloadable components
    resolve their store. Component benchmarks instantiate model classes without
    booting the DashAI app; the download mixin reads
    di["config"]["COMPONENT_PATH"] at call time, so the default local path
    store (~/.DashAI/components) is registered here — the same store the app
    and the pipeline benchmarks use.
    """
    from kink import di

    try:
        di["config"]
    except KeyError:
        from DashAI.back.dependencies.config_builder import build_config_dict

        di["config"] = build_config_dict(local_path=None, logging_level="ERROR")


def ensure_component_downloaded(
    component_class: type, *, download: bool = True
) -> None:
    """Ensure a downloadable component's artifacts exist before instantiation.

    No-op for classes without REQUIRES_DOWNLOAD (or lacking the download API).
    When artifacts are missing and download is False, raise RuntimeError naming
    the class and pointing at the shared component store; otherwise download
    them (printing the class name and DOWNLOAD_SIZE_BYTES when known) so the
    download time is never attributed to model load.

    Parameters
    ----------
    component_class : type
        Component class to check (e.g. a GGUF chat model).
    download : bool
        When True, fetch missing artifacts. When False, a missing component
        raises instead of downloading.

    Raises
    ------
    RuntimeError
        If artifacts are missing and ``download`` is False.
    """
    if not getattr(component_class, "REQUIRES_DOWNLOAD", False):
        return

    is_downloaded = getattr(component_class, "is_downloaded", None)
    download_fn = getattr(component_class, "download", None)
    if not callable(is_downloaded) or not callable(download_fn):
        return

    if is_downloaded():
        return

    class_name = component_class.__name__
    if not download:
        raise RuntimeError(
            f"{class_name} artifacts are missing from the shared DashAI "
            "component store. Re-run without --no-download to fetch them, or "
            "download them in the DashAI app first."
        )

    size = getattr(component_class, "DOWNLOAD_SIZE_BYTES", None)
    if size:
        print(f"  Downloading {class_name} ({size} bytes)...")
    else:
        print(f"  Downloading {class_name}...")
    download_fn()


def load_last_run_statuses(
    output_dir: Path,
) -> dict[tuple[str, str, str, str], str]:
    """Map ``(component_type, component_class, model_name, config_name)``
    → latest real status.

    Scans every ``*.csv`` file under *output_dir* (recursively, so run
    subfolders are covered) and, for each component key, keeps the status
    of the most recently timestamped row. Rows are compared by their ISO
    ``timestamp`` column (lexicographic order is valid for ISO timestamps).

    Rows with status ``skipped`` and malformed rows (missing columns, empty
    key parts, unknown status) are ignored so a skip or a truncated write
    never overrides a real ``passed``/``failed`` result.
    """
    entries: dict[tuple[str, str, str, str], tuple[str, str]] = {}
    for csv_file in output_dir.glob("**/*.csv"):
        try:
            with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("status")
                    if status == "skipped" or status not in _STATUS_VALUES:
                        continue
                    timestamp = row.get("timestamp") or ""
                    if not timestamp:
                        continue
                    key = (
                        row.get("component_type") or "",
                        row.get("component_class") or "",
                        row.get("model_name") or "",
                        row.get("config_name") or "",
                    )
                    if any(not part for part in key):
                        continue
                    if key not in entries or timestamp > entries[key][0]:
                        entries[key] = (timestamp, status)
        except (OSError, csv.Error, ValueError):
            # Skip unreadable/malformed CSV files (e.g. interrupted writes);
            # they must not abort the whole --skip-passes scan.
            continue
    return {key: status for key, (_, status) in entries.items()}


def load_passed_pipelines(results_dir: Path) -> set[str]:
    """Return the names of pipelines that passed in their most recent run.

    Scans every ``results.csv`` under *results_dir* (recursively, covering
    each ``<RUN_TIMESTAMP>/pipelines/<index> - <name>/`` run folder) and,
    for each pipeline, evaluates only its most recent run folder. Run
    folder names are ISO timestamps like ``20260802_143500``, comparable
    lexicographically (the largest is the most recent). A pipeline passed
    when its most recent run has at least one iteration and every one of
    those iterations recorded at least one turn and not every turn errored
    (a partial failure is treated as passed, matching ``_pipeline_success``).

    Limitation: a run interrupted before all iterations were written counts
    the recorded iterations only, so a pipeline with missing iterations can
    still be reported as passed. This mirrors the component scan and is
    accepted for the benchmark's incremental output model.

    Rows without a ``pipeline_name`` or ``run_id`` (e.g. component CSVs)
    and unreadable or malformed files are ignored so a truncated write or
    an unrelated CSV never aborts the scan.

    Parameters
    ----------
    results_dir : Path
        Directory containing all run folders (e.g. ``RAG_benchmark/results``).

    Returns
    -------
    set[str]
        The ``pipeline_name`` values (registry names) that passed in their
        most recent run.
    """
    per_pipeline: dict[str, dict[str, dict[str, tuple[int, int]]]] = {}
    for csv_file in results_dir.glob(f"**/{RESULTS_CSV_FILENAME}"):
        try:
            with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pipeline_name = row.get("pipeline_name")
                    run_id = row.get("run_id")
                    if not pipeline_name or not run_id:
                        continue
                    # Layout: <results_dir>/<RUN>/pipelines/<folder>/results.csv,
                    # so the run folder is the second ancestor of the CSV file.
                    run_folder = str(csv_file.parents[2])
                    iterations = per_pipeline.setdefault(pipeline_name, {}).setdefault(
                        run_folder, {}
                    )
                    total, errors = iterations.get(run_id, (0, 0))
                    iterations[run_id] = (
                        total + 1,
                        errors + bool(row.get("error")),
                    )
        except (OSError, csv.Error, ValueError):
            # Skip unreadable/malformed CSV files (e.g. interrupted writes);
            # they must not abort the whole --skip-passes scan.
            continue

    passed: set[str] = set()
    for pipeline_name, run_folders in per_pipeline.items():
        if not run_folders:
            continue
        iterations = run_folders[max(run_folders)]
        if iterations and all(
            total > 0 and errors < total for total, errors in iterations.values()
        ):
            passed.add(pipeline_name)
    return passed


def run_configs(
    configs: List[Dict[str, Any]],
    component_type: str,
    execute_fn,
    logger: BenchmarkLogger,
    skip_statuses: Dict[tuple[str, str, str, str], str] | None = None,
) -> None:
    """Run a list of config dicts through execute_fn, logging results.

    Each execution (including skipped ones) is recorded incrementally via
    ``logger.log`` with its full config and captured inputs/outputs, so a
    crash mid-run never loses already-completed executions.

    Parameters
    ----------
    configs : list[dict[str, Any]]
        Each dict must have at least: component_class, model_name, config_name, params
    component_type : str
        Category name like "llm", "embedding"
    execute_fn : callable(config_dict) -> (status, time_sec, load_time, error_msg)
        Function that performs the actual test and returns
        (status, time, load_time, error).
    logger : BenchmarkLogger
    skip_statuses : dict[(component_type, component_class, model_name,
        config_name), str] or None
        Mapping of component key to the latest recorded status. Configs whose
        key maps to ``"passed"`` are skipped instead of executed.
    """
    for cfg in configs:
        timestamp = datetime.now().isoformat()
        key = (
            component_type,
            cfg.get("component_class", ""),
            cfg.get("model_name", ""),
            cfg.get("config_name", "default"),
        )
        if skip_statuses is not None and skip_statuses.get(key) == "passed":
            result = BenchmarkResult(
                component_type=component_type,
                component_class=cfg.get("component_class", ""),
                model_name=cfg.get("model_name", ""),
                config_name=cfg.get("config_name", "default"),
                params=cfg.get("params", {}),
                status="skipped",
                time_seconds=0.0,
                first_load_time=0.0,
                error_message="",
                timestamp=timestamp,
            )
            logger.log(
                result,
                config=cfg,
                inputs={"config": cfg, "component_type": component_type},
                outputs={
                    "status": "skipped",
                    "time_seconds": 0.0,
                    "first_load_time": 0.0,
                    "error_message": "",
                    "output_size": None,
                },
            )
            print(
                f"  SKIP {result.component_class}[{result.config_name}]: "
                "previously passed"
            )
            continue
        try:
            status, time_sec, load_time, error_msg = execute_fn(cfg)
        except Exception as e:
            status = "failed"
            time_sec = 0.0
            load_time = 0.0
            error_msg = str(e)
        finally:
            # Each model loads ~100MB-2GB into RAM/VRAM and never releases it.
            # With ~40 sequential embedding models, this fills the disk with swap.
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

        result = BenchmarkResult(
            component_type=component_type,
            component_class=cfg.get("component_class", ""),
            model_name=cfg.get("model_name", ""),
            config_name=cfg.get("config_name", "default"),
            params=cfg.get("params", {}),
            status=status,
            time_seconds=time_sec,
            first_load_time=load_time,
            error_message=error_msg or "",
            timestamp=timestamp,
        )
        logger.log(
            result,
            config=cfg,
            inputs={"config": cfg, "component_type": component_type},
            outputs={
                "status": status,
                "time_seconds": time_sec,
                "first_load_time": load_time,
                "error_message": error_msg or "",
                "output_size": None,
            },
        )
        # Print progress
        if status == "passed":
            icon = "PASS"
        elif status == "incorrect":
            icon = "WARN"
        elif status == "failed":
            icon = "FAIL"
        else:
            icon = "SKIP"
        print(
            f"  {icon} {result.component_class}[{result.config_name}]: "
            f"{status} ({time_sec:.2f}s)"
        )
