"""Pytest bootstrap for the standalone RAG benchmark suite tests.

Adds the repository root to ``sys.path`` so the ``RAG_benchmark`` package is
importable regardless of the current working directory. This suite is
self-contained inside ``RAG_benchmark/`` and is **not** part of DashAI.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
