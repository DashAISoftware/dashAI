"""Tests for the component category runner failure reporting."""

from __future__ import annotations

from pathlib import Path

from RAG_benchmark.app.benchmark_utils import BenchmarkResult
from RAG_benchmark.app.components.runner import _run_category
from RAG_benchmark.app.config import BenchmarkConfig


def test_a_category_failure_is_reported_as_a_failed_result(tmp_path: Path) -> None:
    """A runner that raises must not look like a clean empty category."""
    config = BenchmarkConfig(results_dir=tmp_path)

    def boom(logger, **kwargs):
        raise RuntimeError("papers directory missing")

    results = _run_category(config, "retrieval", boom)

    assert len(results) == 1
    failed = results[0]
    assert failed.success is False
    assert failed.error_message == "papers directory missing"
    assert failed.params["status"] == "failed"
    assert failed.params["category"] == "retrieval"


def test_results_logged_before_a_category_failure_are_kept(tmp_path: Path) -> None:
    """A crash mid-category must not discard the executions already written."""
    config = BenchmarkConfig(results_dir=tmp_path)

    def half_then_boom(logger, **kwargs):
        logger.log(
            BenchmarkResult(
                component_type="prompt",
                component_class="SomePrompt",
                model_name="generation",
                config_name="en",
                params={"iteration": 1},
                status="passed",
                time_seconds=0.1,
                first_load_time=0.01,
                error_message="",
                timestamp="2026-11-03T11:43:10",
            ),
            config={"component_class": "SomePrompt"},
            inputs={},
            outputs={},
        )
        raise RuntimeError("replace failed")

    results = _run_category(config, "prompt", half_then_boom)

    assert len(results) == 2
    assert results[0].success is True
    assert results[0].component_name == "SomePrompt[en]"
    assert results[1].success is False
    assert results[1].params["status"] == "failed"
    assert results[1].error_message == "replace failed"
