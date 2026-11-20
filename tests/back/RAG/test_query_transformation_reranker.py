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
from DashAI.back.models.RAG.exceptions import RAGPipelineRuntimeError
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
from DashAI.back.models.RAG.transformation import LLMQueryExpander
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


def _scorer(scores: Dict[int, float], top_k: int = 10):
    """A retriever stand-in whose ``score_chunks`` returns the given distances."""

    def score_chunks(chunk_ids: List[int], query: str):
        scored = [(cid, scores[cid]) for cid in chunk_ids if cid in scores]
        return sorted(scored, key=lambda pair: pair[1])

    return SimpleNamespace(score_chunks=score_chunks, retrieval_top_k=top_k)


class TestRerankChunks:
    """``ChunkScorer.rerank_chunks`` orders a pool by the scorer's distance."""

    def test_orders_by_ascending_distance_and_keeps_top_k(self):
        pool = [_chunk(0), _chunk(1), _chunk(2)]
        retriever = _scorer({0: 0.9, 1: 0.1, 2: 0.5}, top_k=2)

        ranked = ChunkScorer.rerank_chunks(retriever, pool, "query")

        assert [chunk.id for chunk in ranked] == [1, 2]

    def test_empty_pool_is_returned_without_scoring(self):
        def must_not_score(chunk_ids, query):
            raise AssertionError("an empty pool must not be scored")

        retriever = SimpleNamespace(score_chunks=must_not_score, retrieval_top_k=3)

        assert ChunkScorer.rerank_chunks(retriever, [], "query") == []

    def test_unscored_chunks_keep_their_pool_order_after_the_scored_ones(self):
        idless = Chunk(id=None, document_id=1, document_position=0, text="idless")
        pool = [idless, _chunk(1), _chunk(2), _chunk(3)]
        retriever = _scorer({2: 0.2}, top_k=10)

        ranked = ChunkScorer.rerank_chunks(retriever, pool, "query")

        # Chunk 2 is the only scored one; the chunks without an id or outside the
        # index are kept in pool order rather than dropped.
        assert [chunk.document_position for chunk in ranked] == [2, 0, 1, 3]

    def test_ties_keep_the_order_the_scorer_returned(self):
        pool = [_chunk(0), _chunk(1)]
        retriever = _scorer({0: 0.5, 1: 0.5}, top_k=10)

        ranked = ChunkScorer.rerank_chunks(retriever, pool, "query")

        assert [chunk.id for chunk in ranked] == [0, 1]


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


class TestSetupAttachesTheReranker:
    """The reranker is built with the index infrastructure, then attached."""

    def test_configured_reranker_is_built_by_the_index_service_and_attached(self):
        transformer = SimpleNamespace(reranker=None)
        scorer = _FakeScorer("dense")
        service = _Retrievers(model=scorer)

        SetupService._attach_reranker(
            transformer,
            {
                "reranker": {
                    "component": "DenseEmbeddingRetriever",
                    "params": {"top_k": 5},
                }
            },
            service,
        )

        assert service.built == [("DenseEmbeddingRetriever", {"top_k": 5})]
        assert transformer.reranker is scorer

    def test_null_reranker_builds_nothing(self):
        transformer = SimpleNamespace(reranker=None)
        service = _Retrievers()

        SetupService._attach_reranker(transformer, {"reranker": None}, service)

        assert service.built == []
        assert transformer.reranker is None

    def test_absent_reranker_builds_nothing(self):
        transformer = SimpleNamespace(reranker=None)
        service = _Retrievers()

        SetupService._attach_reranker(transformer, {}, service)

        assert service.built == []

    def test_configured_reranker_without_an_index_service_fails_loudly(self):
        transformer = SimpleNamespace(reranker=None)

        with pytest.raises(RuntimeError, match="retrieval index"):
            SetupService._attach_reranker(
                transformer,
                {"reranker": {"component": "DenseEmbeddingRetriever", "params": {}}},
                None,
            )

    def test_reranker_without_the_scorer_capability_is_refused(self):
        transformer = SimpleNamespace(reranker=None)
        service = _Retrievers(model=SimpleNamespace(name="not a scorer"))

        with pytest.raises(RuntimeError, match="ChunkScorer"):
            SetupService._attach_reranker(
                transformer,
                {"reranker": {"component": "ParallelRetriever", "params": {}}},
                service,
            )
        assert transformer.reranker is None


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
