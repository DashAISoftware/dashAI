"""Behaviour of the query transformation reranker, which is a retriever.

Any retriever can reorder a pool it did not retrieve: its ``score_chunks``
ranks the pool's chunk ids against the original message, and the best
``retrieval_top_k`` are kept. These tests pin that contract and its wiring:
the pool ordering, the context budget priced through the reranker, the single
query exemption, and the attachment built with the index infrastructure.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List

import pytest

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import (
    RAGPipelineRuntimeError,
    RAGRetrieverRerankError,
    RAGTransformationConfigError,
)
from DashAI.back.models.RAG.RAG_pipeline import RAGPipeline
from DashAI.back.models.RAG.retrievers.capabilities import ChunkScorer
from DashAI.back.models.RAG.retrievers.composite.agentic_ensemble_retriever import (
    AgenticEnsembleRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
    MMRRerankerRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.parallel_retriever import (
    ParallelRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever
from DashAI.back.models.RAG.retrievers.trace_utils import chunk_ref
from DashAI.back.models.RAG.transformation import (
    LLMQueryExpander,
    LLMQueryRewriter,
)
from DashAI.back.services.RAG.session_configuration_service import (
    SessionConfigurationService,
)
from DashAI.back.services.RAG.setup_service import SetupService


def _chunk(position: int) -> Chunk:
    return Chunk(
        id=position,
        document_id=1,
        document_position=position,
        text=f"chunk {position}",
    )


class _Scorer(ChunkScorer):
    """A chunk scorer whose ``score_chunks`` returns the given distances."""

    def __init__(self, scores: Dict[int, float], top_k: int = 10, chunks=None) -> None:
        self._scores = scores
        self._top_k = top_k
        self.chunks = chunks or {}

    def score_chunks(self, chunk_ids: List[int], query: str):
        scored = [(cid, self._scores[cid]) for cid in chunk_ids if cid in self._scores]
        return sorted(scored, key=lambda pair: pair[1])

    @property
    def retrieval_top_k(self) -> int:
        return self._top_k


def _scorer(scores: Dict[int, float], top_k: int = 10, chunks=None) -> _Scorer:
    return _Scorer(scores, top_k, chunks)


class TestRerankChunks:
    """``ChunkScorer.rerank_chunks`` orders a pool by the scorer's distance."""

    def test_orders_by_ascending_distance_and_keeps_top_k(self):
        pool = [_chunk(0), _chunk(1), _chunk(2)]
        retriever = _scorer({0: 0.9, 1: 0.1, 2: 0.5}, top_k=2)

        ranked = ChunkScorer.rerank_chunks(retriever, pool, "query")

        assert [chunk.id for chunk in ranked] == [1, 2]

    def test_empty_pool_is_returned_without_scoring(self):
        class _MustNotScore(_Scorer):
            def score_chunks(self, chunk_ids, query):
                raise AssertionError("an empty pool must not be scored")

        retriever = _MustNotScore({}, top_k=3)

        assert ChunkScorer.rerank_chunks(retriever, [], "query") == []

    def test_a_chunk_without_an_id_is_an_error(self):
        idless = Chunk(id=None, document_id=1, document_position=0, text="idless")
        pool = [idless, _chunk(1), _chunk(2)]
        retriever = _scorer({1: 0.1, 2: 0.2}, top_k=10)

        with pytest.raises(RAGRetrieverRerankError, match="could not score 1 of"):
            ChunkScorer.rerank_chunks(retriever, pool, "query")

    def test_a_chunk_outside_the_index_is_an_error(self):
        pool = [_chunk(1), _chunk(2), _chunk(3)]
        retriever = _scorer({2: 0.2}, top_k=10)

        with pytest.raises(RAGRetrieverRerankError, match="could not score 2 of"):
            ChunkScorer.rerank_chunks(retriever, pool, "query")

    def test_ties_keep_the_order_the_scorer_returned(self):
        pool = [_chunk(0), _chunk(1)]
        retriever = _scorer({0: 0.5, 1: 0.5}, top_k=10)

        ranked = ChunkScorer.rerank_chunks(retriever, pool, "query")

        assert [chunk.id for chunk in ranked] == [0, 1]

    def test_a_pool_the_scorer_holds_none_of_is_an_error(self):
        pool = [_chunk(1), _chunk(2)]
        retriever = _scorer({99: 0.1}, top_k=10)

        with pytest.raises(RAGRetrieverRerankError, match="could not score"):
            ChunkScorer.rerank_chunks(retriever, pool, "query")

    def test_a_window_is_ranked_by_the_best_chunk_it_covers(self):
        stored = {1: {i: _chunk(i) for i in range(6)}}
        window = Chunk(
            id=4,
            document_id=1,
            document_position=4,
            text="chunk 4 chunk 5",
            source_positions=(4, 5),
        )
        plain = _chunk(2)
        # The window's first chunk (4) is poor, but chunk 5 is the best match.
        retriever = _scorer({2: 0.5, 4: 0.9, 5: 0.1}, top_k=2, chunks=stored)

        ranked = retriever.rerank_chunks([plain, window], "query")

        assert ranked[0] is window


class _FixedRetriever:
    """Returns the same ordered chunks for every query."""

    def __init__(self, chunks: List[Chunk]) -> None:
        self._chunks = chunks

    def retrieve(self, query: str):
        return list(self._chunks), {"component": "Fixed", "query": query}


class _RecordingReranker:
    """Reverses the pool and records every call it receives."""

    def __init__(self) -> None:
        self.calls: List[str] = []

    @classmethod
    def get_representation(cls):
        return None

    def rerank_chunks(self, chunks: List[Chunk], query: str) -> List[Chunk]:
        self.calls.append(query)
        return list(reversed(chunks))


def _pipeline(retriever, reranker) -> RAGPipeline:
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.retriever = retriever
    pipeline.query_transformation = SimpleNamespace(reranker=reranker)
    return pipeline


class TestPipelineReranking:
    """The pipeline reranks merged multi-query pools and nothing else."""

    def test_single_query_keeps_the_retriever_order_and_skips_the_reranker(self):
        chunks = [_chunk(0), _chunk(1), _chunk(2)]
        reranker = _RecordingReranker()
        pipeline = _pipeline(_FixedRetriever(chunks), reranker)

        merged, _ = pipeline.multi_query_retrieval(["only query"], "original message")

        assert [chunk.document_position for chunk in merged] == [0, 1, 2]
        assert reranker.calls == []

    def test_multiple_queries_are_reranked_against_the_original_message(self):
        chunks = [_chunk(0), _chunk(1), _chunk(2)]
        reranker = _RecordingReranker()
        pipeline = _pipeline(_FixedRetriever(chunks), reranker)

        merged, _ = pipeline.multi_query_retrieval(
            ["first", "second"], "original message"
        )

        assert reranker.calls == ["original message"]
        assert [chunk.document_position for chunk in merged] == [2, 1, 0]

    def test_reranking_adds_a_trace_entry_with_the_pool_and_the_kept_chunks(self):
        chunks = [_chunk(0), _chunk(1), _chunk(2)]
        pipeline = _pipeline(_FixedRetriever(chunks), _RecordingReranker())

        merged, trace = pipeline.multi_query_retrieval(
            ["first", "second"], "original message"
        )

        assert [entry.get("query") for entry in trace[:2]] == ["first", "second"]
        assert len(trace) == 3
        stage = trace[2]
        assert stage["stage"] == "rerank"
        assert "retriever" not in stage
        node = stage["reranker"]
        assert node["name"] == "_RecordingReranker"
        assert node["chunks"] == [chunk_ref(chunk) for chunk in merged]
        assert node["pool"] == [chunk_ref(chunk) for chunk in chunks]

    def test_trace_has_no_rerank_entry_without_a_reranker_or_with_one_query(self):
        chunks = [_chunk(0), _chunk(1)]

        _, without = _pipeline(_FixedRetriever(chunks), None).multi_query_retrieval(
            ["a", "b"], "original"
        )
        _, single = _pipeline(
            _FixedRetriever(chunks), _RecordingReranker()
        ).multi_query_retrieval(["a"], "original")

        assert [entry["query"] for entry in without] == ["a", "b"]
        assert [entry["query"] for entry in single] == ["a"]

    def test_reranker_failure_is_wrapped_as_a_pipeline_error(self):
        class _Failing:
            def rerank_chunks(self, chunks, query):
                raise RuntimeError("scorer down")

        pipeline = _pipeline(_FixedRetriever([_chunk(0)]), _Failing())

        with pytest.raises(RAGPipelineRuntimeError, match="pool reranking"):
            pipeline.multi_query_retrieval(["a", "b"], "original")


def _budget_service() -> SessionConfigurationService:
    registry = {"LLMQueryExpander": {"class": LLMQueryExpander}}
    return SessionConfigurationService(db=None, registry=registry)


def _retriever(top_k: int) -> dict:
    return {"component": "DenseEmbeddingRetriever", "params": {"top_k": top_k}}


def _transformation(n_queries: int, reranker_top_k: int | None) -> dict:
    params: dict = {"n_queries": n_queries}
    if reranker_top_k is not None:
        params["reranker"] = {
            "component": "DenseEmbeddingRetriever",
            "params": {"top_k": reranker_top_k},
        }
    return {"component": "LLMQueryExpander", "params": params}


class TestContextBudgetPricesTheReranker:
    """The budget counts the pool the reranker lets through, not the raw merge."""

    def test_single_query_ignores_the_reranker_cap(self):
        count = _budget_service()._retrieval_chunk_count(
            _retriever(4), _transformation(n_queries=1, reranker_top_k=2)
        )

        assert count == 4

    def test_multi_query_pool_is_capped_by_the_reranker_chunk_count(self):
        count = _budget_service()._retrieval_chunk_count(
            _retriever(4), _transformation(n_queries=3, reranker_top_k=5)
        )

        # 4 chunks x 3 queries = 12 merged, trimmed to the reranker's 5.
        assert count == 5

    def test_reranker_with_a_larger_top_k_does_not_inflate_the_pool(self):
        count = _budget_service()._retrieval_chunk_count(
            _retriever(4), _transformation(n_queries=3, reranker_top_k=50)
        )

        assert count == 12

    def test_without_a_reranker_the_whole_merge_is_priced(self):
        count = _budget_service()._retrieval_chunk_count(
            _retriever(4), _transformation(n_queries=3, reranker_top_k=None)
        )

        assert count == 12


class _FakeScorer(ChunkScorer):
    """A minimal chunk scorer, so the attached reranker passes the capability check."""

    def __init__(self, name: str) -> None:
        self.name = name

    def score_chunks(self, chunk_ids, query):
        return []

    @property
    def retrieval_top_k(self) -> int:
        return 3


class _Retrievers:
    """Stands in for the index setup service: records what it is asked to build."""

    def __init__(self, model=None) -> None:
        self.built: List[tuple] = []
        self._model = model

    def setup(self, component: str, params: dict):
        self.built.append((component, params))
        return SimpleNamespace(model=self._model)


def _setup_service() -> SetupService:
    service = SetupService.__new__(SetupService)
    service._registry = {
        "LLMQueryExpander": {"class": LLMQueryExpander},
        "LLMQueryRewriter": {"class": LLMQueryRewriter},
    }
    return service


def _stage_config(component: str, params: dict):
    return SimpleNamespace(
        query_transformation=SimpleNamespace(component=component, params=params)
    )


def _retriever_result(model=None):
    return SimpleNamespace(model=model)


class _Closable:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class TestSetupBuildsTheRerankerWithTheIndex:
    """The reranker is built with the index infrastructure, with progress."""

    def test_configured_reranker_is_built_by_the_index_service(self):
        scorer = _FakeScorer("dense")
        retrievers = _Retrievers(model=scorer)
        progress: list = []
        config = _stage_config(
            "LLMQueryExpander",
            {
                "reranker": {
                    "component": "DenseEmbeddingRetriever",
                    "params": {"top_k": 5},
                }
            },
        )

        built = _setup_service()._build_reranker(
            config,
            retrievers,
            _retriever_result(),
            lambda fraction, message: progress.append(message),
        )

        assert retrievers.built == [("DenseEmbeddingRetriever", {"top_k": 5})]
        assert built.model is scorer
        assert progress == ["Building the reranker"]

    def test_null_or_absent_reranker_builds_nothing(self):
        for params in ({"reranker": None}, {}):
            retrievers = _Retrievers()

            built = _setup_service()._build_reranker(
                _stage_config("LLMQueryExpander", params),
                retrievers,
                _retriever_result(),
                lambda fraction, message: None,
            )

            assert built is None
            assert retrievers.built == []

    def test_no_stage_builds_nothing(self):
        built = _setup_service()._build_reranker(
            SimpleNamespace(query_transformation=None),
            _Retrievers(),
            _retriever_result(),
            lambda fraction, message: None,
        )

        assert built is None

    def test_rewriter_never_builds_a_reranker_it_cannot_use(self):
        retrievers = _Retrievers(model=_FakeScorer("dense"))

        built = _setup_service()._build_reranker(
            _stage_config(
                "LLMQueryRewriter",
                {"reranker": {"component": "DenseEmbeddingRetriever", "params": {}}},
            ),
            retrievers,
            _retriever_result(),
            lambda fraction, message: None,
        )

        assert built is None
        assert retrievers.built == []

    def test_reranker_without_the_scorer_capability_is_refused_and_released(self):
        not_a_scorer = _Closable()
        main = _Closable()

        with pytest.raises(RAGTransformationConfigError, match="ChunkScorer"):
            _setup_service()._build_reranker(
                _stage_config(
                    "LLMQueryExpander",
                    {"reranker": {"component": "ParallelRetriever", "params": {}}},
                ),
                _Retrievers(model=not_a_scorer),
                _retriever_result(main),
                lambda fraction, message: None,
            )

        assert not_a_scorer.closed == 1
        assert main.closed == 1


class TestChunkScorerCapabilityIsResolvedFromTheRegistry:
    """The offered rerankers come from class inheritance, not a list of names."""

    def test_registry_offers_the_scoring_retrievers_and_not_the_fusion_ones(self):
        registry = ComponentRegistry(
            [
                DenseEmbeddingRetriever,
                BM25Retriever,
                MMRRerankerRetriever,
                ParallelRetriever,
                AgenticEnsembleRetriever,
            ]
        )

        offered = {
            entry["class"].__name__
            for entry in registry.get_child_components("ChunkScorer", recursive=True)
        }

        assert {
            "DenseEmbeddingRetriever",
            "BM25Retriever",
            "MMRRerankerRetriever",
        } <= offered
        assert "ParallelRetriever" not in offered
        assert "AgenticEnsembleRetriever" not in offered


class TestRerankTraceFailure:
    """A reranker whose trace node cannot be built fails the stage explicitly."""

    def test_undescribable_reranker_is_a_pipeline_error(self, monkeypatch):
        import DashAI.back.models.RAG.RAG_pipeline as pipeline_module

        def _boom(*args, **kwargs):
            raise RuntimeError("cannot describe")

        monkeypatch.setattr(pipeline_module, "retriever_trace", _boom)
        pipeline = _pipeline(
            _FixedRetriever([_chunk(0), _chunk(1)]), _RecordingReranker()
        )

        with pytest.raises(RAGPipelineRuntimeError, match="describe the pool reranker"):
            pipeline.multi_query_retrieval(["a", "b"], "original")


class TestBuildPipelineReleasesOnFailure:
    """A pipeline that fails to assemble leaves no retriever or reranker loaded."""

    def test_failed_assembly_releases_the_retriever_and_the_reranker(self):
        retriever, reranker = _Closable(), _Closable()
        service = SetupService.__new__(SetupService)
        index = SimpleNamespace(
            retriever=_retriever_result(retriever), reranker=_retriever_result(reranker)
        )
        service.build_index = lambda config: index

        def _fail(config, built_index):
            raise RuntimeError("prompt store down")

        service._pipeline_from_index = _fail

        with pytest.raises(RuntimeError, match="prompt store down"):
            service.build_pipeline(SimpleNamespace())

        assert retriever.closed == 1
        assert reranker.closed == 1
