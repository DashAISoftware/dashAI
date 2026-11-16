"""Centralized configuration for the benchmark suite.

Configuration is loaded from environment variables with sensible defaults.
A ``.env`` file at ``RAG_benchmark/.env`` is loaded automatically if it exists
(using ``python-dotenv``). Explicit constructor parameters take precedence
over environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from RAG_benchmark.app.device import AUTO_DEVICE


def _load_env_file() -> None:
    """Load the ``RAG_benchmark/.env`` file if it exists.

    Uses ``python-dotenv`` if available; silently skips if the package
    is not installed or the file does not exist.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass


# Load .env once at module import time
_load_env_file()

# Names of the subdirectories and files that make up a run folder layout.
COMPONENTS_DIR_NAME = "components"
PIPELINES_DIR_NAME = "pipelines"
CONFIG_FILENAME = "config.json"


@dataclass
class BenchmarkConfig:
    """Immutable configuration for benchmark execution.

    Attributes
    ----------
    results_dir : Path
        Directory for CSV/JSON output (default: ``RAG_benchmark/results``).
    run_dir : Path or None
        Per-run output folder, set by the CLI; overrides where outputs go.
    data_dir : Path
        Permanent directory that hosts the DashAI local data used by
        pipeline benchmarks (SQLite DB + RAG embeddings). It is kept across
        runs so chunk sets, embedding models and embedding matrices are
        recycled instead of recomputed (default: ``RAG_benchmark/data``).
    papers_dir : Path
        Directory containing PDF papers for benchmarks
        (default: ``RAG_benchmark/papers``).
    deepseek_api_key : str or None
        API key for DeepSeek chat (from ``DASHAI_DEEPSEEK_API_KEY`` env / ``.env``).
    openai_api_key : str or None
        API key for OpenAI services (from ``OPENAI_API_KEY`` env / ``.env``).
    deepseek_model : str
        DeepSeek model name (default: ``deepseek-chat``).
    deepseek_base_url : str
        DeepSeek API base URL (default: ``https://api.deepseek.com``).
    iterations : int
        Number of iterations per benchmark configuration (default: 3).
    messages_per_conversation : int
        Number of user-assistant turns per conversation (default: 5).
    llm_device : str
        Device for local LLM inference: ``auto`` (default), ``CPU``, ``GPU``
        or ``CUDA``. ``auto`` resolves to the first GPU llama.cpp reports and
        falls back to ``CPU`` when there is none; the pipeline benchmarks use
        it as the *budget* of a per-pipeline device plan (see
        ``RAG_benchmark.app.device``).
    skip_passes : bool
        If True, skip components that passed in the last benchmark run
        (default: False).
    download_missing_models : bool
        If True, download missing GGUF models into the shared DashAI component
        store on first use and reuse them afterwards (default: True). When
        False, a missing model fails fast instead (``--no-download``).
    """

    results_dir: Path = field(default_factory=lambda: Path("RAG_benchmark") / "results")
    data_dir: Path = field(default_factory=lambda: Path("RAG_benchmark") / "data")
    papers_dir: Path = field(default_factory=lambda: Path("RAG_benchmark") / "papers")
    # Set per-run by the CLI; overrides where outputs go.
    run_dir: Optional[Path] = None

    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    iterations: int = 3
    messages_per_conversation: int = 5
    llm_device: str = AUTO_DEVICE
    skip_passes: bool = False
    download_missing_models: bool = True

    @property
    def output_dir(self) -> Path:
        """Return the directory where this run's outputs are written."""
        return self.run_dir if self.run_dir is not None else self.results_dir

    @property
    def components_dir(self) -> Path:
        """Return the components subdirectory under the output directory."""
        return self.output_dir / COMPONENTS_DIR_NAME

    @property
    def pipelines_dir(self) -> Path:
        """Return the pipelines subdirectory under the output directory."""
        return self.output_dir / PIPELINES_DIR_NAME

    def with_run_dir(self, run_dir: Path) -> "BenchmarkConfig":
        """Return a copy of this config with *run_dir* set."""
        return replace(self, run_dir=run_dir)

    @classmethod
    def from_env(
        cls,
        results_dir: Optional[Path] = None,
        data_dir: Optional[Path] = None,
        iterations: int = 3,
        messages_per_conversation: int = 5,
        llm_device: str = AUTO_DEVICE,
        skip_passes: bool = False,
        download_missing_models: bool = True,
    ) -> "BenchmarkConfig":
        """Create config from environment variables, overriding with explicit params.

        The ``.env`` file at ``RAG_benchmark/.env`` is loaded automatically
        at module import time (see ``_load_env_file``). Environment variables
        take precedence over ``.env`` values, and explicit method parameters
        take precedence over everything.
        """
        return cls(
            results_dir=results_dir or Path("RAG_benchmark") / "results",
            data_dir=data_dir or Path("RAG_benchmark") / "data",
            papers_dir=Path("RAG_benchmark") / "papers",
            deepseek_api_key=os.environ.get("DASHAI_DEEPSEEK_API_KEY"),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            deepseek_model=os.environ.get("DASHAI_DEEPSEEK_MODEL", "deepseek-chat"),
            iterations=iterations,
            messages_per_conversation=messages_per_conversation,
            llm_device=llm_device,
            skip_passes=skip_passes,
            download_missing_models=download_missing_models,
        )
