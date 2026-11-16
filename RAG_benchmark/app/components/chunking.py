"""Chunking component benchmarks.

``time_seconds`` measures ``BaseChunkingModel.chunk()`` on one parsed
benchmark PDF: joining the document items, splitting the text and mapping
every chunk back to its pages. This is the production path and differs from
the old ``get_chunks()`` measurement, which the chunkers no longer provide.

``first_load_time`` covers construction plus a warm ``chunk_text("")`` call
made inside the load timer, which is what forces a chunker to build the
resources it would otherwise create during the first real chunk: a tokenizer
load is then reported as load time instead of chunking time. The warm-up is
best effort, so a chunker that builds nothing on that call keeps its lazy
cost inside ``time_seconds``.
"""

from __future__ import annotations

import copy
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.dataloaders.classes.document_elements import CHUNK_KIND
from DashAI.back.types.value_types import Text
from RAG_benchmark.app.benchmark_data import CHUNKER_MAP, load_paper_documents
from RAG_benchmark.app.benchmark_utils import (
    BenchmarkLogger,
    Timer,
    load_component_class,
    load_last_run_statuses,
    run_configs,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_document import DashAIDocument
    from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
        BaseChunkingModel,
    )

log = logging.getLogger(__name__)

CHUNKER_CONFIGS = [
    {
        "component_class": "CharacterChunkModel",
        "model_name": "CharacterChunk",
        "config_name": "paragraph",
        "params": {"chunk_size": 500, "chunk_overlap": 50},
    },
    {
        "component_class": "CharacterChunkModel",
        "model_name": "CharacterChunk",
        "config_name": "page",
        "params": {"chunk_size": 2000, "chunk_overlap": 200},
    },
    {
        "component_class": "RecursiveCharacterChunkModel",
        "model_name": "RecursiveChar",
        "config_name": "default",
        "params": {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
    },
    {
        "component_class": "RecursiveCharacterChunkModel",
        "model_name": "RecursiveChar",
        "config_name": "small",
        "params": {
            "chunk_size": 200,
            "chunk_overlap": 20,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
    },
    {
        "component_class": "TokenChunkModel",
        "model_name": "e5-mistral",
        "config_name": "default",
        "params": {
            "tokenizer_name": "intfloat/e5-mistral-7b-instruct",
            "chunk_size": 300,
            "chunk_overlap": 60,
        },
    },
    {
        "component_class": "TokenChunkModel",
        "model_name": "bert-spanish",
        "config_name": "default",
        "params": {
            "tokenizer_name": "dccuchile/bert-base-spanish-wwm-uncased",
            "chunk_size": 512,
            "chunk_overlap": 50,
        },
    },
]


@lru_cache(maxsize=1)
def _benchmark_document() -> DashAIDocument:
    """Parse, once per process, the paper every chunker config is measured on.

    Parsing a 43-page PDF costs ~2 s, so doing it per config would waste
    minutes per run and would also be repeated by every iteration.

    Returns
    -------
    DashAIDocument
        The first benchmark PDF, parsed by ``PypdfDocumentDataLoader``.

    Raises
    ------
    FileNotFoundError
        If ``RAG_benchmark/papers`` holds no PDF. Nothing is cached on
        failure, so every config records the same actionable error instead
        of aborting the whole benchmark run.
    """
    return load_paper_documents(max_docs=1)[0]


#: Text the warm-up call chunks. Non-empty on purpose: a chunker may return
#: early for empty input (``TokenChunkModel`` does), which would leave the
#: tokenizer to be built during the first real chunk instead of at load time.
_WARM_UP_TEXT = "Warm-up document."


def _warm_chunker(chunker: BaseChunkingModel) -> None:
    """Force the resources a chunker builds on its first ``chunk_text`` call.

    ``TokenChunkModel`` loads its tokenizer lazily, which would otherwise be
    timed as chunking work while ``first_load_time`` claimed the model was
    free to build. The warm-up input is discarded and a failure is only
    logged at debug level: warming must never turn a working chunker into a
    failed row.

    Parameters
    ----------
    chunker : BaseChunkingModel
        A freshly constructed chunking model.
    """
    try:
        chunker.chunk_text(_WARM_UP_TEXT)
    except Exception as error:
        log.debug("Warm-up of %s failed: %s", type(chunker).__name__, error)


def _assert_chunk_items(
    component_class: str, source: DashAIDocument, chunks: DashAIDocument
) -> None:
    """Check a chunked document holds non-empty text chunks covering the source.

    Parameters
    ----------
    component_class : str
        Name of the chunker that produced ``chunks``, used in messages.
    source : DashAIDocument
        The parsed document the chunker was given.
    chunks : DashAIDocument
        The document returned by ``BaseChunkingModel.chunk()``.
    """
    items = chunks.items()
    assert items, f"{component_class} produced no chunk items"
    text_items = [item for item in items if item.type is Text]
    assert text_items, f"{component_class} produced no text chunks"
    for item in text_items:
        assert item.kind == CHUNK_KIND, (
            f"{component_class} produced item kind {item.kind!r}, "
            f"expected {CHUNK_KIND!r}"
        )
        assert isinstance(item.content, str), (
            f"{component_class} produced non-text chunk content"
        )
        assert item.content.strip(), f"{component_class} produced an empty chunk"
    assert all(item.page is not None for item in text_items), (
        f"{component_class} chunks are missing page provenance"
    )
    source_chars = sum(
        len(item.content) for item in source.items() if item.type is Text
    )
    chunk_chars = sum(len(item.content.strip()) for item in text_items)
    assert chunk_chars >= source_chars / 2, (
        f"{component_class} chunks cover {chunk_chars} of {source_chars} characters"
    )


def _execute_chunker(cfg: dict[str, Any]) -> tuple[str, float, float, str]:
    """Build a chunker from its config and chunk the first benchmark paper.

    ``params`` keeps the injected ``iteration`` / ``total_iterations`` so the
    recorded config matches ``configs.json``; schema validation ignores them.

    Parameters
    ----------
    cfg : dict[str, Any]
        Chunker config with ``component_class`` and ``params`` keys.

    Returns
    -------
    tuple[str, float, float, str]
        ``(status, exec_seconds, load_seconds, error)``.
    """
    class_name = cfg["component_class"]
    params = dict(cfg["params"])
    chunker_class = load_component_class(CHUNKER_MAP, class_name)
    document = _benchmark_document()

    with Timer() as load_timer:
        chunker = chunker_class(**params)
        _warm_chunker(chunker)

    with Timer() as exec_timer:
        chunked = chunker.chunk(document)

    _assert_chunk_items(class_name, document, chunked)

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def run_all_chunking_benchmarks(
    logger: BenchmarkLogger,
    iterations: int = 1,
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
) -> None:
    """Run all chunker benchmarks, optionally skipping previously passed configs.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    """
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    for iteration in range(1, iterations + 1):
        configs = []
        for cfg in CHUNKER_CONFIGS:
            c = copy.deepcopy(cfg)
            c.setdefault("params", {})["iteration"] = iteration
            c.setdefault("params", {})["total_iterations"] = iterations
            configs.append(c)
        run_configs(
            configs, "chunker", _execute_chunker, logger, skip_statuses=statuses
        )
