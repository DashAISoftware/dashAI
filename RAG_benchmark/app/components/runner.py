"""Centralised runner for component-level benchmarks."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

from RAG_benchmark.app.benchmark_utils import (
    BenchmarkLogger,
    ensure_component_store,
)
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.models import (
    BenchmarkSuiteResult,
    ComponentBenchmarkResult,
)

from .chunking import run_all_chunking_benchmarks
from .embedding import run_all_embedding_benchmarks
from .llm import run_all_llm_benchmarks
from .prompts import run_all_prompt_benchmarks
from .retrieval import run_all_retrieval_benchmarks
from .transformation import run_all_transformation_benchmarks

log = logging.getLogger(__name__)

#: Component categories that can be benchmarked; the default set when the
#: CLI does not restrict the run to specific categories.
COMPONENT_CATEGORIES = [
    "chunking",
    "retrieval",
    "embedding",
    "llm",
    "transformation",
    "prompt",
]

#: Category name -> folder name under the run's ``components/`` directory.
COMPONENT_FOLDER_NAMES = {
    "chunking": "chunking",
    "retrieval": "retrievers",
    "embedding": "embeddings",
    "llm": "llms",
    "transformation": "transformations",
    "prompt": "prompts",
}

#: Category name -> the ``run_all_*_benchmarks`` entry point for that category.
_CATEGORY_RUNNERS: Dict[str, Callable[..., None]] = {
    "chunking": run_all_chunking_benchmarks,
    "retrieval": run_all_retrieval_benchmarks,
    "embedding": run_all_embedding_benchmarks,
    "llm": run_all_llm_benchmarks,
    "transformation": run_all_transformation_benchmarks,
    "prompt": run_all_prompt_benchmarks,
}

#: Categories whose runners accept the device and download flags.
_DEVICE_AWARE_CATEGORIES = ("embedding", "retrieval", "llm", "transformation")


def run_component_benchmarks(
    config: BenchmarkConfig,
    categories: Optional[List[str]] = None,
) -> BenchmarkSuiteResult:
    """Run component-level benchmarks for the requested categories.

    Parameters
    ----------
    config : BenchmarkConfig
        Benchmark configuration.
    categories : list[str] or None
        Component categories to run (e.g. ``chunking``, ``retrieval``).
        Defaults to all registered categories.

    Returns
    -------
    BenchmarkSuiteResult
        Aggregated component results with a summary.
    """
    ensure_component_store()
    start_time = datetime.now()
    suite_result = BenchmarkSuiteResult(
        suite_name="RAG Component Benchmarks",
        start_time=start_time,
        config_snapshot={
            "iterations": config.iterations,
            "categories": categories or COMPONENT_CATEGORIES,
            "has_openai": config.openai_api_key is not None,
        },
    )
    if categories is None:
        categories = COMPONENT_CATEGORIES
    else:
        # Remove duplicates (e.g. repeated --category flags) while keeping
        # the original order so no category runs or logs twice.
        categories = list(dict.fromkeys(categories))

    all_results: List[ComponentBenchmarkResult] = []
    for category in categories:
        runner_fn = _CATEGORY_RUNNERS.get(category)
        if runner_fn is None:
            log.warning("Unknown component category: %s", category)
            continue
        extra_kwargs = (
            {
                "device": config.llm_device,
                "download_missing_models": config.download_missing_models,
            }
            if category in _DEVICE_AWARE_CATEGORIES
            else {}
        )
        all_results.extend(_run_category(config, category, runner_fn, extra_kwargs))

    suite_result.component_results = all_results
    suite_result.end_time = datetime.now()
    total_duration = (suite_result.end_time - suite_result.start_time).total_seconds()
    successful = sum(1 for r in all_results if r.success)
    skipped = sum(1 for r in all_results if r.params.get("status") == "skipped")
    suite_result.summary = {
        "total_executions": len(all_results),
        "successful": successful,
        "skipped": skipped,
        "failed": len(all_results) - successful - skipped,
        "total_duration_seconds": total_duration,
        "categories_run": categories,
    }
    return suite_result


def _run_category(
    config: BenchmarkConfig,
    category: str,
    runner_fn: Callable[..., None],
    extra_kwargs: Optional[Dict[str, object]] = None,
) -> List[ComponentBenchmarkResult]:
    """Run one category through its benchmark entry point.

    Creates a dedicated ``BenchmarkLogger`` writing into the category's
    folder under ``config.components_dir``, runs the category, and converts
    the logged results into ``ComponentBenchmarkResult`` objects.

    Parameters
    ----------
    config : BenchmarkConfig
        Benchmark configuration.
    category : str
        Category name, used to pick the output subfolder.
    runner_fn : callable
        The ``run_all_*_benchmarks`` entry point for the category.
    extra_kwargs : dict or None
        Additional keyword arguments forwarded to ``runner_fn``.

    Returns
    -------
    list[ComponentBenchmarkResult]
        The converted results for the category; empty on failure.
    """
    log.info("Running %s benchmarks...", category)
    print(f"\n  Running {category} benchmarks...")
    logger: Optional[BenchmarkLogger] = None
    try:
        folder_name = COMPONENT_FOLDER_NAMES.get(category, category)
        logger = BenchmarkLogger(output_dir=config.components_dir / folder_name)
        runner_fn(
            logger,
            iterations=config.iterations,
            skip_passes=config.skip_passes,
            results_dir=config.results_dir,
            **(extra_kwargs or {}),
        )
        results = _convert_logger_results(logger, category)
        print(f"    -> {len(results)} executions")
        return results
    except Exception as e:
        log.error("%s benchmarks failed: %s", category, e)
        print(f"    -> FAILED: {e}")
        # Executions already logged are real data: keep them and add the
        # category failure, so a crash near the end does not make the summary
        # report the whole category as lost.
        results = (
            _convert_logger_results(logger, category) if logger is not None else []
        )
        results.append(
            ComponentBenchmarkResult(
                component_name=f"{category}[category-failure]",
                params={
                    "category": category,
                    "status": "failed",
                    "error_message": str(e),
                },
                execution_time_ms=0.0,
                success=False,
                error_message=str(e),
                iteration=0,
            )
        )
        return results


def _convert_logger_results(
    logger: BenchmarkLogger, category: str
) -> List[ComponentBenchmarkResult]:
    """Map the flat logger results of *category* to Pydantic models.

    Parameters
    ----------
    logger : BenchmarkLogger
        The logger that recorded the category's executions.
    category : str
        Category name, stored in each result's params.

    Returns
    -------
    list[ComponentBenchmarkResult]
        One converted result per logged execution.
    """
    converted: List[ComponentBenchmarkResult] = []
    for r in logger.results:
        converted.append(
            ComponentBenchmarkResult(
                component_name=f"{r.component_class}[{r.config_name}]",
                params={
                    "component_class": r.component_class,
                    "config_name": r.config_name,
                    "model_name": r.model_name,
                    "category": category,
                    "status": r.status,
                    **r.params,
                },
                execution_time_ms=r.time_seconds * 1000,
                success=r.status == "passed",
                error_message=r.error_message if r.error_message else None,
                iteration=r.params.get("iteration", 1),
            )
        )
    return converted
