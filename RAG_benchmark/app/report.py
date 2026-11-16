"""Console summary output for benchmark suite results.

The per-run files (``results.csv``, ``configs.json``, ``io.json``) are
written incrementally during execution by the benchmark loggers and
writers; this module only prints a human-readable summary.
"""

from __future__ import annotations

import json

from RAG_benchmark.app.models import BenchmarkSuiteResult


def print_summary(result: BenchmarkSuiteResult) -> None:
    """Print a console summary of the completed benchmark suite."""
    print("\n" + "=" * 60)
    print(f"  Benchmark Suite: {result.suite_name}")
    print(f"  Started: {result.start_time}")
    print(f"  Ended:   {result.end_time or 'N/A'}")
    print("=" * 60)
    if result.component_results:
        components = result.component_results
        success_count = sum(1 for r in components if r.success)
        print(
            f"\n  Component Benchmarks: {len(components)} runs, "
            f"{success_count} successful"
        )
        avg_time = sum(r.execution_time_ms for r in components if r.success)
        if success_count:
            print(f"  Avg execution time: {avg_time / success_count:.2f} ms")
    if result.pipeline_results:
        pipelines = result.pipeline_results
        success_count = sum(1 for r in pipelines if r.success)
        skipped_count = sum(1 for r in pipelines if r.skipped)
        print(
            f"\n  Pipeline Benchmarks: {len(pipelines)} runs, "
            f"{success_count} successful, {skipped_count} skipped"
        )
        for pipe in pipelines:
            if pipe.skipped:
                print(f"    {pipe.pipeline_name}: SKIPPED (already passed)")
            elif pipe.success:
                print(
                    f"    {pipe.pipeline_name} (iter {pipe.iteration}): "
                    f"{len(pipe.turns)} turns, avg {pipe.avg_turn_time_ms:.0f} ms/turn "
                    f"(transform {pipe.avg_transformation_time_ms:.0f}, "
                    f"retrieve {pipe.avg_retrieval_time_ms:.0f}, "
                    f"generate {pipe.avg_generation_time_ms:.0f})"
                )
            else:
                print(
                    f"    {pipe.pipeline_name} (iter {pipe.iteration}): "
                    f"FAILED - {pipe.error_message}"
                )
    if result.summary:
        print(f"\n  Summary: {json.dumps(result.summary, indent=4)}")
    print("=" * 60 + "\n")
