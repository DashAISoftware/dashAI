"""Runner for pipeline-level benchmarks.

Orchestrates the execution of all thesis pipeline configurations
and aggregates results into Pydantic models.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from RAG_benchmark.app.benchmark_utils import load_passed_pipelines
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.models import BenchmarkSuiteResult, PipelineRunResult

from .base import PipelineBenchmarkRunner
from .configs import PIPELINE_REGISTRY

log = logging.getLogger(__name__)


def _failed_pipeline_result(pipeline_name: str, error: str) -> PipelineRunResult:
    """Build a failed result for a pipeline that never reached its iterations."""
    return PipelineRunResult(
        pipeline_name=pipeline_name,
        pipeline_config={},
        document_ids=[],
        turns=[],
        total_time_ms=0.0,
        avg_retrieval_time_ms=0.0,
        avg_generation_time_ms=0.0,
        avg_turn_time_ms=0.0,
        total_chunks_retrieved=0,
        success=False,
        error_message=error,
    )


def run_pipeline_benchmarks(
    config: BenchmarkConfig,
    pipelines: Optional[List[str]] = None,
    resolved_device: Optional[str] = None,
) -> BenchmarkSuiteResult:
    """Run the specified pipeline benchmarks.

    When ``config.skip_passes`` is enabled, pipelines whose most recent
    recorded run passed are skipped and reported with ``skipped=True``;
    only missing or previously-failed pipelines are executed.

    Parameters
    ----------
    config : BenchmarkConfig
        Benchmark configuration.
    pipelines : list[str] or None
        List of pipeline keys to run (e.g., ["pub1", "pub2"]).
        If None, all registered pipelines are run.
    resolved_device : str or None
        Device label ``config.llm_device`` resolved to (``CPU`` or a llama.cpp
        GPU label). Every pipeline then plans which of its llama.cpp
        components fits on that GPU. When None, the raw ``config.llm_device``
        is handed over and resolved by the runner.

    Returns
    -------
    BenchmarkSuiteResult
        Aggregated results from all pipeline benchmarks.
    """
    start_time = datetime.now()
    requested_device = resolved_device or config.llm_device
    suite_result = BenchmarkSuiteResult(
        suite_name="RAG Pipeline Benchmarks",
        start_time=start_time,
        config_snapshot={
            "iterations": config.iterations,
            "messages_per_conversation": config.messages_per_conversation,
            "llm_device": config.llm_device,
            "llm_device_resolved": requested_device,
            "skip_passes": config.skip_passes,
            "has_deepseek": config.deepseek_api_key is not None,
            "has_openai": config.openai_api_key is not None,
            "data_dir": str(config.data_dir),
            "papers_dir": str(config.papers_dir),
        },
    )

    if pipelines is None:
        pipeline_keys = list(PIPELINE_REGISTRY.keys())
    else:
        pipeline_keys = [k for k in pipelines if k in PIPELINE_REGISTRY]
        missing = set(pipelines) - set(PIPELINE_REGISTRY.keys())
        if missing:
            log.warning("Unknown pipelines: %s", sorted(missing))

    if not pipeline_keys:
        suite_result.end_time = datetime.now()
        suite_result.summary = {"error": "No valid pipelines to run"}
        return suite_result

    passed_pipelines = (
        load_passed_pipelines(config.results_dir) if config.skip_passes else set()
    )

    all_pipeline_results: List[PipelineRunResult] = []
    to_run: List[Tuple[int, str]] = []
    for i, key in enumerate(pipeline_keys):
        entry = PIPELINE_REGISTRY[key]
        if config.skip_passes and entry["name"] in passed_pipelines:
            log.info("Skipping passed pipeline: %s (%s)", key, entry["name"])
            print(f"\n  Skipping {entry['name']} (already passed)...")
            all_pipeline_results.append(
                PipelineRunResult(
                    pipeline_name=entry["name"],
                    pipeline_config={},
                    document_ids=[],
                    turns=[],
                    total_time_ms=0.0,
                    avg_retrieval_time_ms=0.0,
                    avg_generation_time_ms=0.0,
                    avg_turn_time_ms=0.0,
                    total_chunks_retrieved=0,
                    success=False,
                    skipped=True,
                )
            )
        else:
            to_run.append((i, key))

    runner: Optional[PipelineBenchmarkRunner] = None
    runner_initialized = False
    run_error: Optional[str] = None
    try:
        if to_run:
            runner = PipelineBenchmarkRunner(config, requested_device=requested_device)
            runner.setup()
            runner_initialized = True

            for i, key in to_run:
                entry = PIPELINE_REGISTRY[key]
                log.info("Running pipeline: %s (%s)", key, entry["name"])
                print(f"\n  Running {entry['name']}...")

                try:
                    preflight_params = entry["config_fn"]([])
                    runner.ensure_models_available(
                        preflight_params,
                        download=config.download_missing_models,
                    )
                except Exception as e:
                    log.error("Pipeline %s model pre-flight failed: %s", key, e)
                    print(f"    -> FAILED: {e}")
                    all_pipeline_results.append(
                        _failed_pipeline_result(entry["name"], str(e))
                    )
                    continue

                results = runner.run_pipeline(
                    pipeline_key=key,
                    pipeline_name=entry["name"],
                    config_fn=entry["config_fn"],
                    iterations=config.iterations,
                    messages_per_conversation=config.messages_per_conversation,
                    pipeline_index=i + 1,
                )
                all_pipeline_results.extend(results)

        suite_result.pipeline_results = all_pipeline_results

    except Exception as e:
        log.error("Pipeline benchmark suite failed: %s", e)
        run_error = str(e)
    finally:
        if runner_initialized:
            runner.teardown()

    suite_result.end_time = datetime.now()
    total_duration = (suite_result.end_time - suite_result.start_time).total_seconds()
    if run_error is not None:
        suite_result.summary = {
            "error": run_error,
            "total_duration_seconds": total_duration,
            "pipelines": list(pipeline_keys),
        }
    else:
        successful = sum(1 for r in all_pipeline_results if r.success)
        skipped = sum(1 for r in all_pipeline_results if r.skipped)
        suite_result.summary = {
            "total_pipelines_run": len(all_pipeline_results),
            "successful": successful,
            "skipped": skipped,
            "failed": len(all_pipeline_results) - successful - skipped,
            "total_duration_seconds": total_duration,
            "pipelines": list(pipeline_keys),
        }

    return suite_result
