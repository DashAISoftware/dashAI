"""Pipeline-level benchmarks for thesis RAG configurations."""
from RAG_benchmark.app.pipelines.configs import PIPELINE_REGISTRY
from RAG_benchmark.app.pipelines.runner import run_pipeline_benchmarks

__all__ = [
    "PIPELINE_REGISTRY",
    "run_pipeline_benchmarks",
]
