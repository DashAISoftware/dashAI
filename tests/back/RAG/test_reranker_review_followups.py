"""Behaviours added when the transformation reranker was reviewed.

Covers the retriever cleanup (the reranker shares its pipeline's rows with the
retriever stage), composite row reuse, and the context budget of a reranked
pool.
"""

from __future__ import annotations

from typing import Any, Dict

from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.transformation import LLMQueryDecomposer
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService
from DashAI.back.services.RAG.session_configuration_service import (
    SessionConfigurationService,
)
from tests.back.RAG.conftest import _insert_rag_session

BM25 = "BM25Retriever"
TFIDF = "TFIDFRetriever"


def _bm25(top_k: int) -> Dict[str, Any]:
    return {"component": BM25, "params": {"top_k": top_k}}


def _parameters(retriever: Dict[str, Any], reranker: Any) -> Dict[str, Any]:
    """Session parameters carrying a retriever and an optional reranker."""
    params: Dict[str, Any] = {"prompt": {"component": "P", "params": {}}}
    if reranker is not None:
        params["reranker"] = reranker
    return {
        "retriever_model": retriever,
        "query_transformation": {"component": "LLMQueryExpander", "params": params},
        "documents": [],
    }


class _Index:
    """A pipeline with one chunk set and helpers to add fitted sparse rows."""

    def __init__(self, db, tmp_path, session_id: int) -> None:
        self.db = db
        self.tmp_path = tmp_path
        chunk_set = RAGChunkSet(signature=f"sig-{session_id}", parameters={})
        chunk_set.session_id = session_id
        db.add(chunk_set)
        db.add(RAGPipeline(session_id=session_id, name=""))
        db.flush()
        self.chunk_set_id = chunk_set.id
        self.pipeline_id = (
            db.query(RAGPipeline).filter_by(session_id=session_id).one().id
        )

    def sparse(self, class_name: str, params: Dict[str, Any]) -> int:
        """Add a fitted sparse retriever row and return its bridge id."""
        bridge = RAGRetriever(class_name=class_name, pipeline_id=self.pipeline_id)
        self.db.add(bridge)
        self.db.flush()
        folder = self.tmp_path / f"sparse_{bridge.id}"
        folder.mkdir()
        self.db.add(
            RAGSparseRetriever(
                bridge_id=bridge.id,
                chunk_set_id=self.chunk_set_id,
                class_name=class_name,
                parameters=dict(sorted(params.items())),
                storage_folder=str(folder),
            )
        )
        self.db.commit()
        return bridge.id

    def exists(self, bridge_id: int) -> bool:
        return self.db.get(RAGRetriever, bridge_id) is not None


def _index(orm_db, tmp_path, name: str):
    session = _insert_rag_session(orm_db, name)
    return session, _Index(orm_db, tmp_path, session.id)


class TestCleanupDoesNotMixTheTwoStages:
    """The retriever stage and the reranker keep their rows in one pipeline."""

    def test_changing_the_retriever_keeps_a_same_class_reranker(self, orm_db, tmp_path):
        session, index = _index(orm_db, tmp_path, "mix_a")
        # The reranker's row is the lowest id, so a lookup by class name alone
        # would return it instead of the retriever's own row.
        reranker_bridge = index.sparse(BM25, {"top_k": 3})
        main_bridge = index.sparse(BM25, {"top_k": 5})
        old = _parameters(_bm25(5), _bm25(3))
        new = _parameters({"component": TFIDF, "params": {"top_k": 5}}, _bm25(3))

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, new)

        assert not index.exists(main_bridge)
        assert index.exists(reranker_bridge)

    def test_a_row_shared_by_both_stages_survives_a_retriever_change(
        self, orm_db, tmp_path
    ):
        session, index = _index(orm_db, tmp_path, "mix_shared")
        shared = index.sparse(BM25, {"top_k": 5})
        old = _parameters(_bm25(5), _bm25(5))
        new = _parameters({"component": TFIDF, "params": {"top_k": 5}}, _bm25(5))

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, new)

        assert index.exists(shared)

    def test_changing_only_the_reranker_deletes_its_rows_and_not_the_retrievers(
        self, orm_db, tmp_path
    ):
        session, index = _index(orm_db, tmp_path, "mix_rerank_only")
        main_bridge = index.sparse(BM25, {"top_k": 5})
        reranker_bridge = index.sparse(BM25, {"top_k": 3})
        old = _parameters(_bm25(5), _bm25(3))
        new = _parameters(_bm25(5), None)

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, new)

        assert index.exists(main_bridge)
        assert not index.exists(reranker_bridge)
        assert orm_db.query(RAGSparseRetriever).count() == 1

    def test_an_unchanged_reranker_is_left_alone(self, orm_db, tmp_path):
        session, index = _index(orm_db, tmp_path, "mix_unchanged")
        main_bridge = index.sparse(BM25, {"top_k": 5})
        reranker_bridge = index.sparse(BM25, {"top_k": 3})
        parameters = _parameters(_bm25(5), _bm25(3))

        CleanupService(orm_db).cleanup_orphaned_resources(
            session.id, parameters, _parameters(_bm25(5), _bm25(3))
        )

        assert index.exists(main_bridge)
        assert index.exists(reranker_bridge)

    def test_deleting_the_session_removes_the_reranker_rows_too(self, orm_db, tmp_path):
        session, index = _index(orm_db, tmp_path, "mix_delete")
        main_bridge = index.sparse(BM25, {"top_k": 5})
        reranker_bridge = index.sparse(BM25, {"top_k": 3})

        CleanupService(orm_db).cleanup_orphaned_resources(
            session.id, _parameters(_bm25(5), _bm25(3)), None
        )

        assert not index.exists(main_bridge)
        assert not index.exists(reranker_bridge)


class TestCompositeRowsAreReused:
    """Setting the same composite up every turn must not add rows."""

    def test_same_children_reuse_the_composite_row(self, orm_db, tmp_path):
        _, index = _index(orm_db, tmp_path, "composite_reuse")
        first_child = index.sparse(BM25, {"top_k": 5})
        second_child = index.sparse(TFIDF, {"top_k": 5})
        service = RetrieverDBService(orm_db)

        first = service.save_composite(
            "ParallelRetriever", index.pipeline_id, [first_child, second_child]
        )
        again = service.save_composite(
            "ParallelRetriever", index.pipeline_id, [first_child, second_child]
        )

        assert again.id == first.id
        assert orm_db.query(RAGRetrieverChild).count() == 2

    def test_other_children_or_order_create_a_new_composite(self, orm_db, tmp_path):
        _, index = _index(orm_db, tmp_path, "composite_new")
        first_child = index.sparse(BM25, {"top_k": 5})
        second_child = index.sparse(TFIDF, {"top_k": 5})
        service = RetrieverDBService(orm_db)

        first = service.save_composite(
            "ParallelRetriever", index.pipeline_id, [first_child, second_child]
        )
        swapped = service.save_composite(
            "ParallelRetriever", index.pipeline_id, [second_child, first_child]
        )
        sequential = service.save_composite(
            "SequentialRetriever", index.pipeline_id, [first_child, second_child]
        )

        assert len({first.id, swapped.id, sequential.id}) == 3


def _budget_service() -> SessionConfigurationService:
    registry = {"LLMQueryDecomposer": {"class": LLMQueryDecomposer}}
    return SessionConfigurationService(db=None, registry=registry)


def _expanding(top_k: int, window: int) -> Dict[str, Any]:
    return {
        "component": "DenseEmbeddingRetriever",
        "params": {
            "top_k": top_k,
            "enable_retrieve_then_expand": True,
            "expand_window": window,
        },
    }


def _decomposition(max_subqueries: Any, reranker: Any) -> Dict[str, Any]:
    params: Dict[str, Any] = {"max_subqueries": max_subqueries}
    if reranker is not None:
        params["reranker"] = reranker
    return {"component": "LLMQueryDecomposer", "params": params}


class TestBudgetOfARerankedPool:
    """The reranker keeps units; their width comes from the retriever stage."""

    def test_kept_units_are_as_wide_as_the_retrievers_expansion_window(self):
        reranker = {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}

        count = _budget_service()._retrieval_chunk_count(
            _expanding(4, 3), _decomposition(3, reranker)
        )

        # 4 units x 3 queries = 12 units of 3 chunks each (36), cut to the
        # reranker's 5 units of 3 chunks.
        assert count == 15

    def test_the_rerankers_own_expansion_window_does_not_widen_the_pool(self):
        retriever = {"component": "DenseEmbeddingRetriever", "params": {"top_k": 4}}

        count = _budget_service()._retrieval_chunk_count(
            retriever, _decomposition(3, _expanding(5, 7))
        )

        assert count == 5

    def test_an_uncapped_decomposition_is_priced_at_the_rerankers_cap(self):
        retriever = {"component": "DenseEmbeddingRetriever", "params": {"top_k": 1}}
        reranker = {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}

        count = _budget_service()._retrieval_chunk_count(
            retriever, _decomposition(None, reranker)
        )

        # Three declared queries would only price 3 chunks; the model may emit
        # more, so the reranker's cap of 5 is the safe bound.
        assert count == 5

    def test_an_uncapped_decomposition_without_a_reranker_keeps_the_declared_count(
        self,
    ):
        retriever = {"component": "DenseEmbeddingRetriever", "params": {"top_k": 4}}

        count = _budget_service()._retrieval_chunk_count(
            retriever, _decomposition(None, None)
        )

        assert count == 12
