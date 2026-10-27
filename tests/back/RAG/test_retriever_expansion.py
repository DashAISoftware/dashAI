"""Unit tests for the shared retrieve-then-expand feature.

Every retriever exposes the same two options: ``enable_retrieve_then_expand``
and ``expand_window``. When enabled, the retriever's **final** output is
expanded into centred windows of ``expand_window`` stored chunks and overlapping
windows are merged into a single concatenated unit; chunks that already carry
``source_positions`` keep their covered range and only take part in the merge.

The tests cover the window/merge arithmetic through the protected helpers, the
schema contract shared by the eleven retriever schemas, the option validation,
the pipeline's cross-query merge, and three integrations (a real
``BM25Retriever`` leaf, a ``ParallelRetriever`` composite and a cross-encoder
whose score trace must label expanded units).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pytest
from pydantic import ValidationError

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import RAGRetrieverError
from DashAI.back.models.RAG.RAG_pipeline import _chunk_label, merge_round_robin
from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_depth_retriever import (
    LLMEvaluatedDepthRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_ensemble_retriever import (  # noqa: E501
    LLMEvaluatedEnsembleRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.composite.llm_filter_retriever import (
    LLMFilterRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
    MMRRerankerRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.composite.parallel_retriever import (
    ParallelRetriever,
    ParallelRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.composite.sequential_retriever import (
    SequentialRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.cross_encoder.cross_encoder_retriever import (
    CrossEncoderRetriever,
)
from DashAI.back.models.RAG.retrievers.cross_encoder.sentence_transformer_cross_encoder import (  # noqa: E501
    SentenceTransformerCrossEncoderRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import (
    DenseRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.enums import MergeStrategy
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND,
    DEFAULT_EXPAND_WINDOW,
    ENABLE_FIELD,
    MAX_EXPAND_WINDOW,
    WINDOW_FIELD,
    RetrievalExpansionSchema,
)
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import (
    BM25Retriever,
    BM25RetrieverSchema,
    BM25VectorizerModel,
)
from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import (
    TFIDFRetrieverSchema,
)
from DashAI.back.models.RAG.retrievers.trace_utils import retriever_trace

DOCUMENT_ID = 1
OTHER_DOCUMENT_ID = 2
CORPUS_SIZE = 10

#: Document positions of the sparse corpus, deliberately not ``0..n-1``.
SPARSE_POSITIONS = (0, 1, 2, 10, 11, 12, 13)


def _corpus(
    size: int = CORPUS_SIZE, document_id: int = DOCUMENT_ID
) -> Dict[int, Dict[int, Chunk]]:
    """Build ``{document_id: {position: Chunk}}`` with ``c<position>`` texts."""
    chunks: Dict[int, Chunk] = {}
    for position in range(size):
        chunks[position] = Chunk(
            id=document_id * 100 + position,
            document_id=document_id,
            document_position=position,
            text=f"c{position}",
            page=position + 1,
        )
    return {document_id: chunks}


def _sparse_corpus() -> Dict[int, Dict[int, Chunk]]:
    """Build a document whose chunk positions are not 0-based contiguous."""
    chunks: Dict[int, Chunk] = {}
    for position in SPARSE_POSITIONS:
        chunks[position] = Chunk(
            id=DOCUMENT_ID * 100 + position,
            document_id=DOCUMENT_ID,
            document_position=position,
            text=f"c{position}",
            page=position + 1,
        )
    return {DOCUMENT_ID: chunks}


def _positions_by_document(retrieved: List[Chunk]) -> List[Tuple[int, int]]:
    """Return ``(document_id, document_position)`` pairs for retrieved units."""
    return [(chunk.document_id, chunk.document_position) for chunk in retrieved]


class _ExpansionRetriever(BaseRetriever):
    """Minimal retriever exposing the shared expansion helper."""

    def __init__(self, **kwargs):
        """Forward the configuration to the base retriever."""
        super().__init__(**kwargs)

    def retrieve(self, query: str, **kwargs) -> Tuple[List[Chunk], Dict[str, object]]:
        """Return no chunks; the tests call the expansion helper directly."""
        return [], retriever_trace(self, [])

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Return no scores."""
        return []

    @property
    def retrieval_top_k(self) -> int:
        """Return a fixed top-k."""
        return 1


class _FixedRetriever(BaseRetriever):
    """Child retriever returning a fixed chunk list, for composite tests."""

    def __init__(self, chunks: List[Chunk]):
        """Store the chunks this child always returns."""
        super().__init__()
        self._fixed_chunks = chunks

    def retrieve(self, query: str, **kwargs) -> Tuple[List[Chunk], Dict[str, object]]:
        """Return the fixed chunks and their trace node."""
        return list(self._fixed_chunks), retriever_trace(self, self._fixed_chunks)

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Return a zero distance for every requested chunk."""
        return [(chunk_id, 0.0) for chunk_id in chunk_ids]

    @property
    def retrieval_top_k(self) -> int:
        """Return the number of fixed chunks."""
        return len(self._fixed_chunks)


def _expansion_retriever(
    chunks: Dict[int, Dict[int, Chunk]],
    *,
    enabled: bool = True,
    window: int = DEFAULT_EXPAND_WINDOW,
) -> _ExpansionRetriever:
    """Build a helper retriever with an injected corpus."""
    retriever = _ExpansionRetriever(
        enable_retrieve_then_expand=enabled,
        expand_window=window,
    )
    retriever.inject_infra(".", chunks, None)
    return retriever


# ── Pure expansion behaviour ─────────────────────────────────────────────────


def test_expansion_disabled_returns_original_chunks():
    """The default configuration leaves the retrieved chunks untouched."""
    corpus = _corpus()
    retriever = _ExpansionRetriever()
    retriever.inject_infra(".", corpus, None)
    retrieved = [corpus[DOCUMENT_ID][4], corpus[DOCUMENT_ID][5]]

    result = retriever._apply_retrieval_expansion(retrieved)

    assert result is retrieved
    assert [chunk.document_position for chunk in result] == [4, 5]
    assert all(chunk.source_positions is None for chunk in result)


def test_expansion_window_centers_on_retrieved_chunk():
    """An odd window is centred exactly and inherits the first chunk's data."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][4]])

    assert len(expanded) == 1
    unit = expanded[0]
    assert unit.document_position == 3
    assert unit.text == "c3 c4 c5"
    assert unit.source_positions == (3, 4, 5)
    first = corpus[DOCUMENT_ID][3]
    assert unit.id == first.id
    assert unit.page == first.page


def test_expansion_clamps_at_document_start():
    """A window over the first chunk keeps a full window without underflow."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][0]])

    assert expanded[0].source_positions == (0, 1, 2)
    assert expanded[0].text == "c0 c1 c2"


def test_expansion_clamps_at_document_end():
    """A window over the last chunk is shifted back to keep a full window."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][9]])

    assert expanded[0].source_positions == (7, 8, 9)
    assert expanded[0].document_position == 7
    assert expanded[0].text == "c7 c8 c9"


def test_even_window_places_extra_chunk_after_center():
    """An even window keeps the extra chunk after the retrieved one."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus, window=2)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][4]])

    assert expanded[0].source_positions == (4, 5)


def test_overlapping_expansions_merge_into_single_unit():
    """Two overlapping windows become one concatenated unit."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion(
        [corpus[DOCUMENT_ID][2], corpus[DOCUMENT_ID][3]]
    )

    assert len(expanded) == 1
    assert expanded[0].document_position == 1
    assert expanded[0].source_positions == (1, 2, 3, 4)
    assert expanded[0].text == "c1 c2 c3 c4"


def test_overlap_merging_is_transitive():
    """Chained windows collapse into a single unit through transitivity."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion(
        [
            corpus[DOCUMENT_ID][2],
            corpus[DOCUMENT_ID][4],
            corpus[DOCUMENT_ID][6],
        ]
    )

    assert len(expanded) == 1
    assert expanded[0].source_positions == (1, 2, 3, 4, 5, 6, 7)
    assert expanded[0].text == "c1 c2 c3 c4 c5 c6 c7"


def test_non_overlapping_expansions_stay_separate():
    """Disjoint windows stay separate and keep the retrieval order."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion(
        [corpus[DOCUMENT_ID][1], corpus[DOCUMENT_ID][7]]
    )

    assert _positions_by_document(expanded) == [
        (DOCUMENT_ID, 0),
        (DOCUMENT_ID, 6),
    ]


def test_windows_across_documents_never_merge():
    """Identical positions in different documents stay separate units."""
    corpus = _corpus()
    corpus.update(_corpus(document_id=OTHER_DOCUMENT_ID))
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion(
        [corpus[DOCUMENT_ID][0], corpus[OTHER_DOCUMENT_ID][0]]
    )

    assert _positions_by_document(expanded) == [
        (DOCUMENT_ID, 0),
        (OTHER_DOCUMENT_ID, 0),
    ]
    assert expanded[0].text == "c0 c1 c2"
    assert expanded[1].text == "c0 c1 c2"


def test_results_are_ordered_by_first_retrieval_occurrence():
    """Units are ordered by retrieval order, not by document position."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion(
        [corpus[DOCUMENT_ID][5], corpus[DOCUMENT_ID][2]]
    )

    assert _positions_by_document(expanded) == [
        (DOCUMENT_ID, 4),
        (DOCUMENT_ID, 1),
    ]


def test_already_expanded_chunks_are_not_re_expanded():
    """A chunk carrying ``source_positions`` keeps its covered range."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    already = Chunk(
        id=103,
        document_id=DOCUMENT_ID,
        document_position=3,
        text="c3 c4 c5",
        page=4,
        source_positions=(3, 4, 5),
    )

    expanded = retriever._apply_retrieval_expansion([already])

    assert len(expanded) == 1
    assert expanded[0].document_position == 3
    assert expanded[0].source_positions == (3, 4, 5)
    assert expanded[0].text == "c3 c4 c5"
    assert expanded[0].page == 4


def test_unknown_document_is_returned_unchanged():
    """A chunk whose document is not in the corpus is returned unchanged."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    unknown = Chunk(
        id=900,
        document_id=OTHER_DOCUMENT_ID,
        document_position=0,
        text="outside the corpus",
    )

    expanded = retriever._apply_retrieval_expansion([unknown])

    assert len(expanded) == 1
    assert expanded[0] is unknown
    assert expanded[0].source_positions is None


def test_non_contiguous_positions_expand_around_the_retrieved_position():
    """Sparse document positions resolve to the real neighbouring chunks."""
    corpus = _sparse_corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][10]])

    assert len(expanded) == 1
    unit = expanded[0]
    assert unit.document_position == 10
    assert unit.source_positions == (10, 11, 12)
    assert unit.text == "c10 c11 c12"


def test_non_contiguous_positions_clamp_at_the_document_end():
    """The sparse document's last position keeps a full window."""
    corpus = _sparse_corpus()
    retriever = _expansion_retriever(corpus)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][13]])

    assert expanded[0].document_position == 11
    assert expanded[0].source_positions == (11, 12, 13)


def test_expanded_unit_merges_with_overlapping_plain_chunk():
    """A fixed expanded window and a widened plain chunk collapse into one."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    fixed = Chunk(
        id=101,
        document_id=DOCUMENT_ID,
        document_position=1,
        text="c1 c2 c3",
        page=2,
        source_positions=(1, 2, 3),
    )

    expanded = retriever._apply_retrieval_expansion([fixed, corpus[DOCUMENT_ID][4]])

    assert len(expanded) == 1
    unit = expanded[0]
    assert unit.document_position == 1
    assert unit.source_positions == (1, 2, 3, 4, 5)
    assert unit.text == "c1 c2 c3 c4 c5"


def test_window_larger_than_document_covers_every_chunk():
    """A window bigger than the document clamps to all its chunks."""
    corpus = _corpus(size=2)
    retriever = _expansion_retriever(corpus, window=5)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][1]])

    assert expanded[0].document_position == 0
    assert expanded[0].source_positions == (0, 1)
    assert expanded[0].text == "c0 c1"


def test_single_chunk_document_returns_the_stored_chunk():
    """A window with no neighbour returns the stored chunk unchanged."""
    corpus = _corpus(size=1)
    retriever = _expansion_retriever(corpus, window=3)
    chunk = corpus[DOCUMENT_ID][0]

    expanded = retriever._apply_retrieval_expansion([chunk])

    assert len(expanded) == 1
    assert expanded[0] is chunk
    assert expanded[0].source_positions is None
    assert _chunk_label(expanded[0]) == "chunk nº 0"


def test_window_equal_to_document_length_covers_every_chunk():
    """``expand_window`` equal to the document length keeps the whole document."""
    corpus = _corpus(size=4)
    retriever = _expansion_retriever(corpus, window=4)

    expanded = retriever._apply_retrieval_expansion([corpus[DOCUMENT_ID][2]])

    assert expanded[0].source_positions == (0, 1, 2, 3)
    assert expanded[0].text == "c0 c1 c2 c3"


def test_expansion_of_empty_retrieval_returns_empty_list():
    """Expanding nothing returns nothing."""
    retriever = _expansion_retriever(_corpus())

    assert retriever._apply_retrieval_expansion([]) == []


def test_duplicate_retrieved_chunk_yields_one_unit():
    """The same chunk retrieved twice produces a single unit."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    chunk = corpus[DOCUMENT_ID][4]

    expanded = retriever._apply_retrieval_expansion([chunk, chunk])

    assert len(expanded) == 1
    assert expanded[0].source_positions == (3, 4, 5)


def test_window_one_returns_the_same_chunks_without_merging():
    """A window of one adds no context and leaves a plain list untouched."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus, window=1)
    retrieved = [corpus[DOCUMENT_ID][4], corpus[DOCUMENT_ID][5]]

    expanded = retriever._apply_retrieval_expansion(retrieved)
    copy = retriever.expand_retrieved_chunks(retrieved, 1)

    assert expanded == retrieved
    assert expanded is retrieved
    assert copy == retrieved
    assert copy is not retrieved
    assert copy[0] is retrieved[0]


# ── Cross-query merge ────────────────────────────────────────────────────────


def test_cross_query_merge_keeps_plain_chunks_unchanged():
    """``merge_expanded_chunks`` never widens a plain chunk."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    plain = corpus[DOCUMENT_ID][4]

    merged = retriever.merge_expanded_chunks([plain])

    assert len(merged) == 1
    assert merged[0] is plain


def test_cross_query_merge_collapses_overlapping_windows():
    """Overlapping units from different queries collapse into one."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    first = retriever.expand_retrieved_chunks([corpus[DOCUMENT_ID][2]], 3)
    second = retriever.expand_retrieved_chunks([corpus[DOCUMENT_ID][4]], 3)

    merged = merge_round_robin([first, second])
    collapsed = retriever.merge_expanded_chunks(merged)

    assert len(merged) == 2
    assert len(collapsed) == 1
    assert collapsed[0].document_position == 1
    assert collapsed[0].source_positions == (1, 2, 3, 4, 5)
    assert collapsed[0].text == "c1 c2 c3 c4 c5"


def test_plain_chunk_inside_an_expanded_window_is_absorbed():
    """A plain chunk covered by a unit does not appear twice."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    unit = retriever.expand_retrieved_chunks([corpus[DOCUMENT_ID][3]], 3)[0]

    merged = retriever.merge_expanded_chunks([unit, corpus[DOCUMENT_ID][3]])

    assert len(merged) == 1
    assert merged[0].source_positions == (2, 3, 4)
    assert merged[0].text == "c2 c3 c4"


def test_plain_chunk_outside_an_expanded_window_stays_separate():
    """A plain chunk outside the covered range keeps its own place and order."""
    corpus = _corpus()
    retriever = _expansion_retriever(corpus)
    unit = retriever.expand_retrieved_chunks([corpus[DOCUMENT_ID][3]], 3)[0]
    plain = corpus[DOCUMENT_ID][7]

    merged = retriever.merge_expanded_chunks([unit, plain])

    assert len(merged) == 2
    assert merged[0] is unit
    assert merged[1] is plain


# ── Composite with the flag off ──────────────────────────────────────────────


def test_composite_with_expansion_off_merges_expanded_children():
    """A composite whose flag is off still collapses its children's overlaps."""
    corpus = _corpus()
    helper = _expansion_retriever(corpus)
    first = helper.expand_retrieved_chunks([corpus[DOCUMENT_ID][2]], 3)[0]
    second = helper.expand_retrieved_chunks([corpus[DOCUMENT_ID][4]], 3)[0]
    retriever = ParallelRetriever(
        children=[_FixedRetriever([first]), _FixedRetriever([second])],
        merge_strategy=MergeStrategy.ROUND_ROBIN.value,
        enable_retrieve_then_expand=False,
    )
    retriever.inject_infra(".", corpus, None)

    retrieved, _ = retriever.retrieve("anything")

    assert len(retrieved) == 1
    assert retrieved[0].source_positions == (1, 2, 3, 4, 5)


# ── Same-anchor dedup keeps the wider window ─────────────────────────────────


def _narrow_unit() -> Chunk:
    """Return an expanded unit covering positions 2..3."""
    return Chunk(
        id=102,
        document_id=DOCUMENT_ID,
        document_position=2,
        text="c2 c3",
        page=3,
        source_positions=(2, 3),
    )


def _wide_unit() -> Chunk:
    """Return an expanded unit anchored on 2 but covering 2..6."""
    return Chunk(
        id=102,
        document_id=DOCUMENT_ID,
        document_position=2,
        text="c2 c3 c4 c5 c6",
        page=3,
        source_positions=(2, 3, 4, 5, 6),
    )


def test_pipeline_merge_keeps_the_wider_unit():
    """The pipeline merge keeps the widest unit of a repeated anchor."""
    narrow = _narrow_unit()
    wide = _wide_unit()

    forward = merge_round_robin([[narrow], [wide]])
    backward = merge_round_robin([[wide], [narrow]])

    assert forward == [wide]
    assert forward[0] is wide
    assert backward == [wide]
    assert backward[0] is wide


def test_parallel_merge_keeps_the_wider_unit():
    """Both parallel merge strategies keep the widest unit of a repeated anchor."""
    corpus = _corpus()
    for strategy in (MergeStrategy.ROUND_ROBIN, MergeStrategy.INTERLEAVE):
        retriever = ParallelRetriever(
            children=[
                _FixedRetriever([_narrow_unit()]),
                _FixedRetriever([_wide_unit()]),
            ],
            merge_strategy=strategy.value,
        )
        retriever.inject_infra(".", corpus, None)

        retrieved, _ = retriever.retrieve("anything")
        reversed_retriever = ParallelRetriever(
            children=[
                _FixedRetriever([_wide_unit()]),
                _FixedRetriever([_narrow_unit()]),
            ],
            merge_strategy=strategy.value,
        )
        reversed_retriever.inject_infra(".", corpus, None)
        reversed_retrieved, _ = reversed_retriever.retrieve("anything")

        assert len(retrieved) == 1
        assert retrieved[0].source_positions == (2, 3, 4, 5, 6)
        assert len(reversed_retrieved) == 1
        assert reversed_retrieved[0].source_positions == (2, 3, 4, 5, 6)


# ── Option validation ────────────────────────────────────────────────────────


@pytest.mark.parametrize("flag", ["false", "true", 0, 1, None])
def test_invalid_expansion_flag_is_rejected(flag):
    """A non-boolean switch is rejected instead of being coerced."""
    with pytest.raises(RAGRetrieverError, match=ENABLE_FIELD):
        _ExpansionRetriever(**{ENABLE_FIELD: flag})


@pytest.mark.parametrize("window", ["3", 0, -1, 2.5, True, MAX_EXPAND_WINDOW + 1, 1000])
def test_invalid_expand_window_is_rejected(window):
    """A non-integer or out-of-range window is rejected instead of being coerced."""
    with pytest.raises(RAGRetrieverError, match=WINDOW_FIELD):
        _ExpansionRetriever(**{WINDOW_FIELD: window})


# ── Schema contract ──────────────────────────────────────────────────────────

EXPANSION_SCHEMAS = [
    DenseRetrieverSchema,
    DenseEmbeddingRetrieverSchema,
    BM25RetrieverSchema,
    TFIDFRetrieverSchema,
    SentenceTransformerCrossEncoderRetrieverSchema,
    LLMFilterRetrieverSchema,
    LLMEvaluatedDepthRetrieverSchema,
    LLMEvaluatedEnsembleRetrieverSchema,
    MMRRerankerRetrieverSchema,
    ParallelRetrieverSchema,
    SequentialRetrieverSchema,
]


@pytest.mark.parametrize("schema_cls", EXPANSION_SCHEMAS, ids=lambda cls: cls.__name__)
def test_all_retriever_schemas_expose_expansion_fields(schema_cls):
    """Every retriever schema inherits the shared expansion options."""
    assert issubclass(schema_cls, RetrievalExpansionSchema)
    fields = schema_cls.model_fields
    assert "enable_retrieve_then_expand" in fields
    assert "expand_window" in fields
    assert fields["enable_retrieve_then_expand"].default is (
        DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND
    )
    assert fields["expand_window"].default == DEFAULT_EXPAND_WINDOW


def test_expansion_schema_rejects_window_below_one():
    """``expand_window`` is bounded below by one chunk."""
    with pytest.raises(ValidationError):
        RetrievalExpansionSchema.model_validate({"expand_window": 0})


def test_expansion_schema_rejects_window_above_the_maximum():
    """``expand_window`` is bounded above, so one window cannot flood the prompt."""
    with pytest.raises(ValidationError):
        RetrievalExpansionSchema.model_validate({WINDOW_FIELD: MAX_EXPAND_WINDOW + 1})


@pytest.mark.parametrize("window", [True, "3", 3.0])
def test_expansion_schema_rejects_coerced_windows(window):
    """The schema rejects values the constructor would reject instead of coercing."""
    with pytest.raises(ValidationError):
        RetrievalExpansionSchema.model_validate({WINDOW_FIELD: window})


@pytest.mark.parametrize("flag", ["false", "true", 0, 1, None])
def test_expansion_schema_rejects_coerced_flags(flag):
    """The schema rejects a non-boolean switch instead of coercing it."""
    with pytest.raises(ValidationError):
        RetrievalExpansionSchema.model_validate({ENABLE_FIELD: flag})


def test_expansion_schema_accepts_the_bounds():
    """The maximum window and a real boolean are accepted."""
    validated = RetrievalExpansionSchema.model_validate(
        {ENABLE_FIELD: True, WINDOW_FIELD: MAX_EXPAND_WINDOW}
    )

    assert validated.expand_window == MAX_EXPAND_WINDOW
    assert validated.enable_retrieve_then_expand is True


# ── Robustness ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("window", [True, "3", 0, -1, MAX_EXPAND_WINDOW + 1])
def test_expand_retrieved_chunks_rejects_an_invalid_window(window):
    """The public expansion helper validates the window plugins pass in."""
    retriever = _expansion_retriever(_corpus())

    with pytest.raises(RAGRetrieverError, match=WINDOW_FIELD):
        retriever.expand_retrieved_chunks([], window)


# ── Integrations ─────────────────────────────────────────────────────────────


def _bm25_retriever(corpus: Dict[int, Dict[int, Chunk]], **overrides) -> BM25Retriever:
    """Build a fitted BM25 retriever over *corpus*."""
    params = {
        "BM25Vectorizer": BM25VectorizerModel(
            strip_accents=None,
            lowercase=True,
            stop_words=None,
            max_df=1.0,
            min_df=0.0,
            max_features=None,
        ),
        "k1": 1.5,
        "b": 0.75,
        "delta": 0.0,
        "similarity_function": "cosine",
        "top_k": 1,
    }
    params.update(overrides)
    retriever = BM25Retriever(**params)
    retriever.inject_infra(".", corpus, SparsePersistence(model_dir=None))
    retriever.init_model()
    return retriever


def test_bm25_retrieve_expands_the_final_result_and_trace():
    """A real sparse retriever expands its final output and trace."""
    corpus = _corpus()
    retriever = _bm25_retriever(
        corpus,
        enable_retrieve_then_expand=True,
        expand_window=3,
    )

    retrieved, trace = retriever.retrieve("c3")

    assert len(retrieved) == 1
    assert retrieved[0].document_position == 2
    assert retrieved[0].source_positions == (2, 3, 4)
    assert retrieved[0].text == "c2 c3 c4"
    assert trace["chunks"] == [f"{DOCUMENT_ID}_2"]


def test_parallel_retriever_merges_child_windows_into_one_unit():
    """A composite expands its own merged output, not its children's."""
    corpus = _corpus()
    first_child = _FixedRetriever([corpus[DOCUMENT_ID][2]])
    second_child = _FixedRetriever([corpus[DOCUMENT_ID][3]])
    retriever = ParallelRetriever(
        children=[first_child, second_child],
        merge_strategy=MergeStrategy.ROUND_ROBIN.value,
        enable_retrieve_then_expand=True,
        expand_window=3,
    )
    retriever.inject_infra(".", corpus, None)

    retrieved, trace = retriever.retrieve("anything")

    assert len(retrieved) == 1
    assert retrieved[0].document_position == 1
    assert retrieved[0].source_positions == (1, 2, 3, 4)
    assert retrieved[0].text == "c1 c2 c3 c4"
    assert trace["chunks"] == [f"{DOCUMENT_ID}_1"]


class _FixedScoreCrossEncoder(CrossEncoderRetriever):
    """Cross-encoder whose score depends only on the chunk's position."""

    SCORES = {2: 1.0, 3: 5.0, 4: 2.0, 5: 4.0}

    def _cross_score(self, query: str, chunks: List[Chunk]) -> List[float]:
        """Score every candidate by its document position."""
        return [self.SCORES[chunk.document_position] for chunk in chunks]


def _cross_encoder_retriever(
    corpus: Dict[int, Dict[int, Chunk]],
    positions: Tuple[int, ...],
    *,
    top_k: int,
) -> _FixedScoreCrossEncoder:
    """Build a fixed-score cross-encoder over the given candidate positions."""
    candidates = [corpus[DOCUMENT_ID][position] for position in positions]
    retriever = _FixedScoreCrossEncoder(
        children=[_FixedRetriever(candidates)],
        top_k=top_k,
        enable_retrieve_then_expand=True,
        expand_window=3,
    )
    retriever.inject_infra(".", corpus, None)
    return retriever


def test_cross_encoder_score_trace_labels_expanded_units():
    """An expanded unit gets a score entry carrying its best covered score."""
    retriever = _cross_encoder_retriever(_corpus(), (3, 4), top_k=1)

    retrieved, trace = retriever.retrieve("anything")

    assert len(retrieved) == 1
    assert retrieved[0].source_positions == (2, 3, 4)
    assert trace["chunks"] == [f"{DOCUMENT_ID}_2"]
    by_ref = {entry["ref"]: entry["score"] for entry in trace["scores"]}
    assert len(trace["scores"]) == 3
    assert by_ref[f"{DOCUMENT_ID}_2"] == 5.0
    assert by_ref[f"{DOCUMENT_ID}_3"] == 5.0
    assert by_ref[f"{DOCUMENT_ID}_4"] == 2.0


def test_cross_encoder_score_trace_upgrades_a_colliding_reference():
    """A unit sharing a candidate's reference upgrades that entry's score."""
    retriever = _cross_encoder_retriever(_corpus(), (2, 3, 4, 5), top_k=1)

    retrieved, trace = retriever.retrieve("anything")

    assert retrieved[0].source_positions == (2, 3, 4)
    by_ref = {entry["ref"]: entry["score"] for entry in trace["scores"]}
    assert len(trace["scores"]) == 4
    assert by_ref[f"{DOCUMENT_ID}_2"] == 5.0
    assert {f"{DOCUMENT_ID}_{position}" for position in (2, 3, 4, 5)} == set(by_ref)
