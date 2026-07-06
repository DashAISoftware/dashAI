import csv
import gc
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BenchmarkResult:
    """A single benchmark test result."""

    component_type: str
    component_class: str
    model_name: str
    config_name: str
    params: dict
    status: str  # "passed", "failed", "skipped"
    time_seconds: float
    first_load_time: float
    error_message: str  # "" if passed, str if failed
    timestamp: str  # ISO format timestamp


class BenchmarkLogger:
    """Logs benchmark results to CSV file and JSON log file simultaneously."""

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = self.output_dir / f"benchmark_{run_id}.csv"
        self.log_path = self.output_dir / f"benchmark_{run_id}.jsonl"
        self.results: list[BenchmarkResult] = []
        self._write_header()

    def _write_header(self):
        """Write CSV header if file is new."""
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "component_type",
                        "component_class",
                        "model_name",
                        "config_name",
                        "params",
                        "status",
                        "time_seconds",
                        "first_load_time",
                        "error_message",
                    ]
                )

    def log(self, result: BenchmarkResult):
        """Append a result to CSV, JSONL, and in-memory list."""
        self.results.append(result)
        # CSV
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    result.timestamp,
                    result.component_type,
                    result.component_class,
                    result.model_name,
                    result.config_name,
                    json.dumps(result.params),
                    result.status,
                    f"{result.time_seconds:.4f}",
                    f"{result.first_load_time:.4f}",
                    result.error_message,
                ]
            )
        # JSONL
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    def summary(self) -> str:
        """Return a human-readable summary string."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        lines = [
            f"\n{'='*60}",
            f"  BENCHMARK SUMMARY",
            f"{'='*60}",
            f"  Total:    {total}",
            f"  Passed:   {passed}",
            f"  Failed:   {failed}",
            f"  Skipped:  {skipped}",
            f"  CSV:      {self.csv_path}",
            f"  JSONL:    {self.log_path}",
            f"{'='*60}",
        ]
        if failed > 0:
            lines.append("\n  FAILURES:")
            for r in self.results:
                if r.status == "failed":
                    lines.append(
                        f"    \u274c {r.component_class}[{r.config_name}]: {r.error_message[:100]}"
                    )
        return "\n".join(lines)


class Timer:
    """Context manager to measure elapsed time."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start


def run_configs(
    configs: list[dict],
    component_type: str,
    execute_fn,
    logger: BenchmarkLogger,
):
    """Run a list of config dicts through execute_fn, logging results.

    Parameters
    ----------
    configs : list[dict]
        Each dict must have at least: component_class, model_name, config_name, params
    component_type : str
        Category name like "llm", "embedding"
    execute_fn : callable(config_dict) -> (status, time_sec, error_msg)
        Function that performs the actual test and returns (status, time, error)
    logger : BenchmarkLogger
    """
    for cfg in configs:
        timestamp = datetime.now().isoformat()
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
        logger.log(result)
        # Print progress
        if status == "passed":
            icon = "\u2705"
        elif status == "failed":
            icon = "\u274c"
        else:
            icon = "\u23ed\ufe0f"
        print(
            f"  {icon} {result.component_class}[{result.config_name}]: {status} ({time_sec:.2f}s)"
        )


def read_benchmark_csv(csv_path: str) -> list[dict]:
    """Read a benchmark CSV and return as list of dicts."""
    results = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["params"] = json.loads(row["params"])
            row["time_seconds"] = float(row["time_seconds"])
            row["first_load_time"] = float(row["first_load_time"])
            results.append(row)
    return results
