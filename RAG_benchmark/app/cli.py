"""CLI entry point for the DashAI RAG benchmark suite.

Usage:
    python -m RAG_benchmark.app.cli components --iter 3
    python -m RAG_benchmark.app.cli pipelines --iter 3 --messages 5
    python -m RAG_benchmark.app.cli pipelines --pipeline pub1 \
        --iter 1 --messages 3
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import typer

from RAG_benchmark.app.benchmark_data import discover_benchmark_paper_files
from RAG_benchmark.app.components.runner import (
    COMPONENT_CATEGORIES,
    run_component_benchmarks,
)
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.device import AUTO_DEVICE, resolve_requested_device
from RAG_benchmark.app.output import (
    create_run_directory,
    update_run_config,
    write_run_config,
)
from RAG_benchmark.app.pipelines.configs import PIPELINE_REGISTRY
from RAG_benchmark.app.pipelines.runner import run_pipeline_benchmarks
from RAG_benchmark.app.report import print_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

app = typer.Typer(
    name="dashai-benchmark",
    help=(
        "DashAI RAG Benchmark Suite — component and pipeline benchmarks "
        "for thesis evaluation."
    ),
)


def _make_config(
    iterations: int,
    messages: int,
    output_dir: str,
    llm_device: str,
    skip_passes: bool = False,
    data_dir: str = "",
    download_missing_models: bool = True,
) -> BenchmarkConfig:
    """Build a ``BenchmarkConfig`` from the CLI option values.

    Parameters
    ----------
    iterations : int
        Iterations per benchmark configuration.
    messages : int
        Messages per conversation (0 for component benchmarks).
    output_dir : str
        Base results directory for this run.
    llm_device : str
        Device for local LLM inference: ``CPU``, ``GPU``, ``CUDA`` or
        ``auto`` (the default, which picks the llama.cpp GPU when one exists).
    skip_passes : bool
        Whether to skip benchmarks that passed in previous runs
        (components and pipelines).
    data_dir : str
        Permanent DashAI data directory (DB + RAG embeddings) recycled
        across runs. Empty means the config default.
    download_missing_models : bool
        Whether missing GGUF models may be downloaded into the shared DashAI
        component store. False maps to ``--no-download`` (fail fast).

    Returns
    -------
    BenchmarkConfig
        The configured benchmark run settings.
    """
    return BenchmarkConfig.from_env(
        results_dir=Path(output_dir) if output_dir else None,
        iterations=iterations,
        messages_per_conversation=messages,
        llm_device=llm_device,
        skip_passes=skip_passes,
        data_dir=Path(data_dir) if data_dir else None,
        download_missing_models=download_missing_models,
    )


@app.command()
def components(
    iterations: int = typer.Option(
        3,
        "--iter",
        "-i",
        min=1,
        help="Number of iterations per benchmark configuration.",
    ),
    output: str = typer.Option(
        "RAG_benchmark/results", "--output", "-o", help="Output directory for results."
    ),
    categories: List[str] = typer.Option(
        [],
        "--category",
        "-c",
        help="Component categories to benchmark (chunking, retrieval, embedding, "
        "llm, transformation, prompt). Can be specified multiple times. "
        "Default: all.",
    ),
    llm_device: str = typer.Option(
        AUTO_DEVICE,
        "--device",
        "-d",
        help="Device for local llama.cpp inference: CPU, GPU, CUDA or auto "
        "(default: auto picks the llama.cpp GPU when one exists).",
    ),
    skip_passes: bool = typer.Option(
        False,
        "--skip-passes",
        help="Skip components whose latest recorded result was 'passed' "
        "(scanned recursively across all run folders in the output "
        "directory). Only missing or previously-failed components are "
        "executed.",
    ),
    data: str = typer.Option(
        "",
        "--data",
        help="Permanent DashAI data directory (DB + RAG embeddings) recycled "
        "across runs. Default: RAG_benchmark/data.",
    ),
    no_download: bool = typer.Option(
        False,
        "--no-download",
        help="Fail instead of downloading missing GGUF models into the shared "
        "DashAI component store (default: download on first use, reused "
        "afterwards).",
    ),
) -> None:
    """Run component-level benchmarks for RAG modules."""
    config = _make_config(
        iterations,
        0,
        output,
        llm_device,
        skip_passes,
        data,
        not no_download,
    )

    run_time = datetime.now()
    run_dir = create_run_directory(config.results_dir, run_time)
    config = config.with_run_dir(run_dir.root)
    write_run_config(
        run_dir,
        command="components",
        start_time=run_time,
        config=config,
        extra={"categories": (categories or COMPONENT_CATEGORIES)},
    )

    print("\n" + "=" * 60)
    print("  DashAI RAG Component Benchmark Suite")
    print(f"  Iterations: {config.iterations}")
    print(f"  Categories: {categories or 'all'}")
    print(f"  Output:     {config.output_dir}")
    print(f"  Skip passed:       {'YES' if config.skip_passes else 'NO'}")
    print("=" * 60)

    result = run_component_benchmarks(
        config, categories=categories if categories else None
    )

    config_path = update_run_config(
        run_dir,
        end_time=result.end_time or datetime.now(),
        completed=True,
        summary=result.summary,
    )

    print("\n  Results written to:")
    print(f"    Config:  {config_path}")
    print(f"    Folder:  {config.output_dir}")
    for subdir in sorted(
        path for path in config.components_dir.iterdir() if path.is_dir()
    ):
        print(f"    {subdir}")
    print_summary(result)


@app.command()
def pipelines(
    iterations: int = typer.Option(
        3,
        "--iter",
        "-i",
        min=1,
        help="Number of independent conversations per pipeline. Every "
        "session loads all papers in the papers directory as its corpus.",
    ),
    messages: int = typer.Option(
        5, "--messages", "-m", help="Number of user-assistant turns per conversation."
    ),
    pipeline: List[str] = typer.Option(
        [],
        "--pipeline",
        "-p",
        help="Specific pipeline key(s) to run (e.g., pub1, pub2). "
        "Can be specified multiple times. Default: all registered pipelines.",
    ),
    output: str = typer.Option(
        "RAG_benchmark/results", "--output", "-o", help="Output directory for results."
    ),
    llm_device: str = typer.Option(
        AUTO_DEVICE,
        "--device",
        "-d",
        help="Device for local llama.cpp inference: CPU, GPU, CUDA or auto "
        "(default: auto picks the llama.cpp GPU when one exists and plans the "
        "offload per pipeline).",
    ),
    skip_passes: bool = typer.Option(
        False,
        "--skip-passes",
        help="Skip pipelines whose latest recorded run passed (scanned "
        "recursively across all run folders in the output directory). "
        "Only missing or previously-failed pipelines are executed.",
    ),
    data: str = typer.Option(
        "",
        "--data",
        help="Permanent DashAI data directory (DB + RAG embeddings) recycled "
        "across runs. Default: RAG_benchmark/data.",
    ),
    no_download: bool = typer.Option(
        False,
        "--no-download",
        help="Fail instead of downloading missing GGUF models into the shared "
        "DashAI component store (default: download on first use, reused "
        "afterwards).",
    ),
) -> None:
    """Run pipeline-level benchmarks from thesis configurations."""
    config = _make_config(
        iterations,
        messages,
        output,
        llm_device,
        skip_passes,
        data,
        not no_download,
    )
    try:
        resolved_device = resolve_requested_device(config.llm_device)
    except ValueError as exc:
        typer.echo(f"Invalid --device value: {exc}", err=True)
        raise typer.Exit(2) from exc

    available = list(PIPELINE_REGISTRY.keys())
    if pipeline:
        selected = [p for p in pipeline if p in PIPELINE_REGISTRY]
        missing = set(pipeline) - set(available)
        if missing:
            typer.echo(
                f"Warning: Unknown pipelines: {sorted(missing)}. "
                f"Available: {available}",
                err=True,
            )
        if not selected:
            typer.echo(f"No valid pipelines selected. Available: {available}", err=True)
            raise typer.Exit(1)
    else:
        selected = available

    run_time = datetime.now()
    run_dir = create_run_directory(config.results_dir, run_time)
    config = config.with_run_dir(run_dir.root)
    write_run_config(
        run_dir,
        command="pipelines",
        start_time=run_time,
        config=config,
        extra={"pipelines": selected, "llm_device_resolved": resolved_device},
    )

    try:
        paper_count = len(discover_benchmark_paper_files(max_docs=None))
    except Exception:
        paper_count = "N/A"

    print("\n" + "=" * 60)
    print("  DashAI RAG Pipeline Benchmark Suite")
    print(f"  Iterations:          {config.iterations}")
    print(f"  Papers found:        {paper_count}")
    print(f"  Messages/turn:       {config.messages_per_conversation}")
    print(f"  Device:              {resolved_device}")
    print(f"  Pipelines:           {selected}")
    print(
        f"  DeepSeek simulator:  "
        f"{'YES' if config.deepseek_api_key else 'NO (fallback)'}"
    )
    print(f"  Papers:              {config.papers_dir}")
    print(f"  Output:              {config.output_dir}")
    print(f"  Skip passed:          {'YES' if config.skip_passes else 'NO'}")
    print("=" * 60)

    result = run_pipeline_benchmarks(
        config, pipelines=selected, resolved_device=resolved_device
    )

    config_path = update_run_config(
        run_dir,
        end_time=result.end_time or datetime.now(),
        completed=True,
        summary=result.summary,
    )

    print("\n  Results written to:")
    print(f"    Config:  {config_path}")
    print(f"    Folder:  {config.output_dir}")
    for subdir in sorted(
        path for path in config.pipelines_dir.iterdir() if path.is_dir()
    ):
        print(f"    {subdir}")
    print_summary(result)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
