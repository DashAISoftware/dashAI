"""Standalone runner for the pipeline benchmark.

Now that DashAI's full import chain works (all deps installed, fasttext
made optional), this runner simply delegates to pytest.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pytest

sys.exit(pytest.main([
    "tests/back/RAG/test_rag_pipeline_api_configs.py",
    "-v",
    "--tb=short",
    "-k", "not benchmark",
]))
