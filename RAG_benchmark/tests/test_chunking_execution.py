"""Execution tests for the chunking component benchmarks.

Runs the real chunkers on a benchmark PDF through the same code path as
``run_all_chunking_benchmarks``. ``TokenChunkModel`` is excluded: it needs a
Hugging Face tokenizer, so it is not part of an offline suite, and its two
configs are verified with the six-config probe described in
``docs/02-component-benchmarks.md``.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import pytest

from DashAI.back.dataloaders.classes.document_elements import CHUNK_KIND
from DashAI.back.types.value_types import Text
from RAG_benchmark.app import benchmark_data
from RAG_benchmark.app.benchmark_data import CHUNKER_MAP, discover_benchmark_paper_files
from RAG_benchmark.app.benchmark_utils import load_component_class
from RAG_benchmark.app.components.chunking import CHUNKER_CONFIGS, _execute_chunker

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_document import DashAIDocument

#: Chunkers that run without network access.
LOCAL_CHUNKER_CLASSES = {"CharacterChunkModel", "RecursiveCharacterChunkModel"}

_LOCAL_CONFIGS = [
    cfg for cfg in CHUNKER_CONFIGS if cfg["component_class"] in LOCAL_CHUNKER_CLASSES
]


@pytest.fixture(scope="module")
def paper() -> DashAIDocument:
    """Parse the first benchmark paper once for the whole module."""
    if not discover_benchmark_paper_files(max_docs=1):
        pytest.skip("No benchmark papers available")
    return benchmark_data.load_paper_documents(max_docs=1)[0]


def _with_iteration_params(cfg: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy a config and inject the params the benchmark runner adds."""
    run_cfg = copy.deepcopy(cfg)
    run_cfg.setdefault("params", {})["iteration"] = 1
    run_cfg.setdefault("params", {})["total_iterations"] = 1
    return run_cfg


def _config_id(cfg: dict[str, Any]) -> str:
    """Build a readable pytest id for a chunker config."""
    return f"{cfg['component_class']}-{cfg['config_name']}"


@pytest.mark.parametrize("cfg", _LOCAL_CONFIGS, ids=_config_id)
def test_execute_chunker_passes_on_a_real_paper(
    cfg: dict[str, Any], paper: DashAIDocument
) -> None:
    """``_execute_chunker`` builds the chunker and chunks a real paper."""
    status, exec_time, load_time, error = _execute_chunker(_with_iteration_params(cfg))

    assert status == "passed", error
    assert error == ""
    assert exec_time > 0
    assert load_time >= 0


@pytest.mark.parametrize("cfg", _LOCAL_CONFIGS, ids=_config_id)
def test_chunk_produces_chunk_items_with_pages(
    cfg: dict[str, Any], paper: DashAIDocument
) -> None:
    """``BaseChunkingModel.chunk`` returns chunk items mapped to pages."""
    chunker_class = load_component_class(CHUNKER_MAP, cfg["component_class"])

    chunker = chunker_class(**cfg["params"])
    chunked = chunker.chunk(paper)

    items = chunked.items()
    assert items, f"{cfg['component_class']} produced no items"
    text_items = [item for item in items if item.type is Text]
    assert text_items, f"{cfg['component_class']} produced no text items"
    for item in text_items:
        assert item.kind == CHUNK_KIND
        assert isinstance(item.content, str)
        assert item.content.strip()
        assert item.page is not None
    assert chunked.metadata["chunker"] == chunker_class.__name__


def test_load_paper_texts_is_the_blank_line_join(paper: DashAIDocument) -> None:
    """``load_paper_texts`` keeps the exact mapping the benchmarks consume."""
    texts = benchmark_data.load_paper_texts(max_docs=1)

    expected = "\n\n".join(paper[Text]).strip()
    assert texts == {0: expected}
    assert texts[0] == texts[0].strip()
