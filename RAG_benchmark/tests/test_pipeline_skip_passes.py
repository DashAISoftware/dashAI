"""Unit tests for the ``--skip-passes`` pipeline benchmark behaviour.

Covers ``load_passed_pipelines`` (the recursive scan that decides which
pipelines already passed) and the skipping path in
``run_pipeline_benchmarks``. No network or DashAI app is required.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

from RAG_benchmark.app.benchmark_utils import load_passed_pipelines
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.models import PipelineRunResult
from RAG_benchmark.app.pipelines.base import PipelineBenchmarkRunner
from RAG_benchmark.app.pipelines.runner import run_pipeline_benchmarks

_HEADER = ["id", "run_id", "pipeline_name", "iteration", "turn_number", "error"]


def _write_pipeline_csv(
    results_dir: Path,
    run_folder: str,
    pipeline_name: str,
    turns: List[Tuple[int, int, str]],
) -> None:
    """Write a minimal per-turn ``results.csv`` for one pipeline run.

    The file lands at ``<results_dir>/<run_folder>/pipelines/1 - <name>/results.csv``
    with the minimal per-turn header and one row per ``(iteration, turn,
    error)`` triple.

    Parameters
    ----------
    results_dir : Path
        Directory that holds all run folders.
    run_folder : str
        Run folder name (ISO timestamp like ``20260802_100000``).
    pipeline_name : str
        Registry ``name`` stored on every row.
    turns : list[tuple[int, int, str]]
        ``(iteration, turn_number, error)`` rows; ``error`` is ``""`` for OK.
    """
    folder = results_dir / run_folder / "pipelines" / f"1 - {pipeline_name}"
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER)
        for iteration, turn_number, error in turns:
            writer.writerow(
                [
                    f"iter{iteration}-turn{turn_number}",
                    f"iter{iteration}",
                    pipeline_name,
                    iteration,
                    turn_number,
                    error,
                ]
            )


def test_load_passed_pipelines_all_iterations_passed(tmp_path: Path) -> None:
    """A pipeline whose every iteration of the latest run passed is returned."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, ""), (0, 1, ""), (1, 0, "")],
    )

    assert load_passed_pipelines(tmp_path) == {"Publication 1 - Medical Fitness"}


def test_load_passed_pipelines_failed_iteration_not_in_set(tmp_path: Path) -> None:
    """An iteration with any errored turn means the pipeline did not pass."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, ""), (1, 0, "boom")],
    )

    assert load_passed_pipelines(tmp_path) == set()


def test_load_passed_pipelines_partial_failure_counts_as_passed(tmp_path: Path) -> None:
    """A partial failure (some turns OK) is treated as passed, like the runner."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, ""), (0, 1, "boom"), (1, 0, "")],
    )

    assert load_passed_pipelines(tmp_path) == {"Publication 1 - Medical Fitness"}


def test_load_passed_pipelines_latest_run_wins(tmp_path: Path) -> None:
    """Only the most recent run folder is evaluated for each pipeline."""
    failed_latest = tmp_path / "failed_latest"
    _write_pipeline_csv(
        failed_latest,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "")],
    )
    _write_pipeline_csv(
        failed_latest,
        "20260802_110000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "boom")],
    )
    assert load_passed_pipelines(failed_latest) == set()

    passed_latest = tmp_path / "passed_latest"
    _write_pipeline_csv(
        passed_latest,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "boom")],
    )
    _write_pipeline_csv(
        passed_latest,
        "20260802_110000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "")],
    )
    assert load_passed_pipelines(passed_latest) == {"Publication 1 - Medical Fitness"}


def test_load_passed_pipelines_ignores_component_csvs(tmp_path: Path) -> None:
    """Component CSVs without a pipeline_name column are ignored."""
    components = tmp_path / "20260802_100000" / "components" / "chunking"
    components.mkdir(parents=True)
    (components / "results.csv").write_text(
        "id,timestamp,component_type,component_class,model_name,config_name,"
        "status,time_seconds,first_load_time,error_message\n"
        "0001,2026-08-02T10:00:00,chunker,ClassA,ModelX,cfg,passed,1.0,0.5,\n",
        encoding="utf-8",
    )

    assert load_passed_pipelines(tmp_path) == set()


def test_load_passed_pipelines_tolerates_bad_csv(tmp_path: Path) -> None:
    """A corrupt CSV is skipped without aborting the scan."""
    bad = tmp_path / "20260802_100000" / "pipelines" / "1 - Bad"
    bad.mkdir(parents=True)
    (bad / "results.csv").write_bytes(b"\xff\xfe\x00 not a csv")

    _write_pipeline_csv(
        tmp_path,
        "20260802_110000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "")],
    )

    assert load_passed_pipelines(tmp_path) == {"Publication 1 - Medical Fitness"}


def test_run_pipeline_benchmarks_skips_passed_pipeline(tmp_path: Path) -> None:
    """run_pipeline_benchmarks skips a pipeline that already passed."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, ""), (1, 0, "")],
    )

    config = BenchmarkConfig(results_dir=tmp_path, skip_passes=True)
    with patch.object(PipelineBenchmarkRunner, "setup") as mock_setup:
        result = run_pipeline_benchmarks(config, pipelines=["pub1"])

    mock_setup.assert_not_called()
    assert len(result.pipeline_results) == 1
    assert result.pipeline_results[0].skipped is True
    assert result.summary["skipped"] == 1


def test_run_pipeline_benchmarks_does_not_skip_without_flag(tmp_path: Path) -> None:
    """Without skip_passes, a previously passed pipeline still runs."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "")],
    )

    config = BenchmarkConfig(results_dir=tmp_path, skip_passes=False)
    with patch(
        "RAG_benchmark.app.pipelines.runner.PipelineBenchmarkRunner"
    ) as mock_runner_cls:
        instance = mock_runner_cls.return_value
        instance.run_pipeline.return_value = []
        result = run_pipeline_benchmarks(config, pipelines=["pub1"])

    instance.setup.assert_called_once()
    assert len(result.pipeline_results) == 0
    assert result.summary["skipped"] == 0


def test_run_pipeline_benchmarks_mixes_skipped_and_run(tmp_path: Path) -> None:
    """Skipped and executed pipelines are both reported in the same run."""
    _write_pipeline_csv(
        tmp_path,
        "20260802_100000",
        "Publication 1 - Medical Fitness",
        [(0, 0, "")],
    )

    config = BenchmarkConfig(results_dir=tmp_path, skip_passes=True)
    with patch(
        "RAG_benchmark.app.pipelines.runner.PipelineBenchmarkRunner"
    ) as mock_runner_cls:
        instance = mock_runner_cls.return_value
        instance.run_pipeline.return_value = [
            PipelineRunResult(
                pipeline_name="Publication 2 - EHR Summarization",
                pipeline_config={},
                document_ids=[],
                turns=[],
                total_time_ms=1.0,
                avg_retrieval_time_ms=0.0,
                avg_generation_time_ms=0.0,
                avg_turn_time_ms=0.0,
                total_chunks_retrieved=0,
                success=True,
            )
        ]
        result = run_pipeline_benchmarks(config, pipelines=["pub1", "pub2"])

    instance.setup.assert_called_once()
    instance.run_pipeline.assert_called_once()
    instance.teardown.assert_called_once()
    assert len(result.pipeline_results) == 2
    assert result.pipeline_results[0].skipped is True
    assert result.pipeline_results[1].skipped is False
    assert result.summary["skipped"] == 1
    assert result.summary["successful"] == 1
