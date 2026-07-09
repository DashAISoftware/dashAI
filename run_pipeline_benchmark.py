"""Thin wrapper that delegates to RAG_benchmark/run_pipeline_benchmark.py.

The actual implementation has moved to ``RAG_benchmark/run_pipeline_benchmark.py``.
Please use that going forward, or run:
    python -m RAG_benchmark.benchmarks.cli [OPTIONS] COMMAND [ARGS]
"""

from __future__ import annotations

import sys
from pathlib import Path

_runner = Path(__file__).parent / "RAG_benchmark" / "run_pipeline_benchmark.py"
if not _runner.exists():
    print(
        "Error: RAG_benchmark/run_pipeline_benchmark.py not found.\n"
        "Please run: python -m RAG_benchmark.benchmarks.cli --help",
        file=sys.stderr,
    )
    sys.exit(1)

# Forward to the moved script
sys.path.insert(0, str(_runner.parent.parent))
from RAG_benchmark.run_pipeline_benchmark import main

if __name__ == "__main__":
    main()
