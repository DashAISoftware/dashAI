"""Behaviours added when the transformation reranker was reviewed.

Covers the retriever cleanup (the reranker shares its pipeline's rows with the
retriever stage), composite row reuse, and the context budget of a reranked
pool.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest

from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.exceptions import RAGPipelineConfigError
from DashAI.back.models.RAG.transformation import LLMQueryDecomposer
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService
from DashAI.back.services.RAG.session_configuration_service import (
    SessionConfigurationService,
)
from tests.back.RAG.conftest import _insert_rag_session

BM25 = "BM25Retriever"
TFIDF = "TFIDFRetriever"
DENSE = "DenseEmbeddingRetriever"
SEQUENTIAL = "SequentialRetriever"


def _bm25(top_k: int) -> Dict[str, Any]:
    return {"component": BM25, "params": {"top_k": top_k}}


def _parameters(
    retriever: Dict[str, Any], reranker: Any, documents: List[int] | None = None
) -> Dict[str, Any]:
    """Session parameters carrying a retriever and an optional reranker."""
    params: Dict[str, Any] = {"prompt": {"component": "P", "params": {}}}
    if reranker is not None:
        params["reranker"] = reranker
    return {
        "retriever_model": retriever,
        "query_transformation": {"component": "LLMQueryExpander", "params": params},
        "documents": documents or [],
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

    def embedding_model(self, name: str) -> int:
        """Add an embedding model row and return its id."""
        model = RAGEmbeddingModel(class_name=name, parameters={})
        self.db.add(model)
        self.db.flush()
        return model.id

    def dense(self, params: Dict[str, Any], embedding_model_id: int) -> int:
        """Add a dense retriever row and return its bridge id."""
        bridge = RAGRetriever(class_name=DENSE, pipeline_id=self.pipeline_id)
        self.db.add(bridge)
        self.db.flush()
        self.db.add(
            RAGDenseRetriever(
                bridge_id=bridge.id,
                chunk_set_id=self.chunk_set_id,
                class_name=DENSE,
                parameters=dict(sorted(params.items())),
                embedding_model_id=embedding_model_id,
            )
        )
        self.db.commit()
        return bridge.id

    def matrix(self, document_id: int, embedding_model_id: int) -> str:
        """Add a stored embedding matrix with a real folder; return the folder."""
        folder = self.tmp_path / f"matrix_{document_id}_{embedding_model_id}"
        folder.mkdir()
        self.db.add(
            RAGEmbeddingMatrix(
                document_id=document_id,
                chunk_set_id=self.chunk_set_id,
                embedding_model_id=embedding_model_id,
                storage_folder=str(folder),
                matrix_shape=[1, 2],
            )
        )
        self.db.commit()
        return str(folder)

    def composite(self, class_name: str, child_ids: List[int]) -> int:
        """Add a composite row linked to the given children, in order."""
        bridge = RAGRetriever(class_name=class_name, pipeline_id=self.pipeline_id)
        self.db.add(bridge)
        self.db.flush()
        for order, child_id in enumerate(child_ids):
            self.db.add(
                RAGRetrieverChild(
                    parent_id=bridge.id, child_id=child_id, child_order=order
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


def _dense(top_k: int) -> Dict[str, Any]:
    return {"component": DENSE, "params": {"top_k": top_k}}


class TestCleanupKeepsSharedDenseMatrices:
    """Dense retrievers with one embedding over one chunk set share matrices."""

    def test_dropping_the_reranker_keeps_the_matrices_the_retriever_reads(
        self, orm_db, tmp_path
    ):
        session, index = _index(orm_db, tmp_path, "dense_shared")
        embedding = index.embedding_model("E")
        main_bridge = index.dense({"top_k": 5}, embedding)
        reranker_bridge = index.dense({"top_k": 3}, embedding)
        folder = index.matrix(1, embedding)
        old = _parameters(_dense(5), _dense(3), documents=[1])
        new = _parameters(_dense(5), None, documents=[1])

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, new)

        assert index.exists(main_bridge)
        assert not index.exists(reranker_bridge)
        assert orm_db.query(RAGEmbeddingMatrix).count() == 1
        assert os.path.isdir(folder)

    def test_a_reranker_with_its_own_embedding_takes_its_matrices_with_it(
        self, orm_db, tmp_path
    ):
        session, index = _index(orm_db, tmp_path, "dense_own")
        main_embedding = index.embedding_model("E_main")
        reranker_embedding = index.embedding_model("E_rerank")
        index.dense({"top_k": 5}, main_embedding)
        index.dense({"top_k": 3}, reranker_embedding)
        main_folder = index.matrix(1, main_embedding)
        reranker_folder = index.matrix(1, reranker_embedding)
        old = _parameters(_dense(5), _dense(3), documents=[1])
        new = _parameters(_dense(5), None, documents=[1])

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, new)

        assert orm_db.query(RAGEmbeddingMatrix).count() == 1
        assert os.path.isdir(main_folder)
        assert not os.path.isdir(reranker_folder)

    def test_deleting_the_session_removes_the_shared_matrices(self, orm_db, tmp_path):
        session, index = _index(orm_db, tmp_path, "dense_delete")
        embedding = index.embedding_model("E")
        index.dense({"top_k": 5}, embedding)
        index.dense({"top_k": 3}, embedding)
        folder = index.matrix(1, embedding)
        old = _parameters(_dense(5), _dense(3), documents=[1])

        CleanupService(orm_db).cleanup_orphaned_resources(session.id, old, None)

        assert orm_db.query(RAGEmbeddingMatrix).count() == 0
        assert not os.path.isdir(folder)


class TestCompositeCleanupMatchesByStoredShape:
    """A composite is found by its ordered children, not by class alone."""

    def test_only_the_composite_with_the_old_children_is_deleted(
        self, orm_db, tmp_path
    ):
        session, index = _index(orm_db, tmp_path, "composite_match")
        bm25_child = index.sparse(BM25, {"top_k": 5})
        tfidf_child = index.sparse(TFIDF, {"top_k": 5})
        old_composite = index.composite(SEQUENTIAL, [bm25_child, tfidf_child])
        other_composite = index.composite(SEQUENTIAL, [tfidf_child, bm25_child])
        old_reference = {
            "component": SEQUENTIAL,
            "params": {
                "children": [_bm25(5), {"component": TFIDF, "params": {"top_k": 5}}]
            },
        }
        new_reference = {"component": TFIDF, "params": {"top_k": 5}}

        CleanupService(orm_db).cleanup_orphaned_resources(
            session.id,
            _parameters(old_reference, None),
            _parameters(new_reference, None),
        )

        assert not index.exists(old_composite)
        assert index.exists(other_composite)

    def test_a_composite_that_matches_no_row_is_swept_by_class(self, orm_db, tmp_path):
        session, index = _index(orm_db, tmp_path, "composite_sweep")
        child = index.sparse(BM25, {"top_k": 9})
        stale = index.composite(SEQUENTIAL, [child])
        old_reference = {
            "component": SEQUENTIAL,
            "params": {"children": [_bm25(5), _bm25(3)]},
        }

        CleanupService(orm_db).cleanup_orphaned_resources(
            session.id,
            _parameters(old_reference, None),
            _parameters({"component": TFIDF, "params": {"top_k": 5}}, None),
        )

        assert not index.exists(stale)


class TestCleanupRejectsMalformedStoredStructure:
    """A stored reference of the wrong shape fails instead of matching nothing."""

    def test_a_composite_reference_without_children_is_rejected(self, orm_db, tmp_path):
        _, index = _index(orm_db, tmp_path, "malformed_composite")
        index.composite(SEQUENTIAL, [])

        with pytest.raises(RAGPipelineConfigError, match="no list of children"):
            CleanupService(orm_db)._matching_bridges(
                index.pipeline_id, {"component": SEQUENTIAL, "params": {}}
            )

    def test_non_dict_params_are_rejected(self, orm_db, tmp_path):
        _, index = _index(orm_db, tmp_path, "malformed_params")

        with pytest.raises(RAGPipelineConfigError, match="not a dict"):
            CleanupService(orm_db)._matching_bridges(
                index.pipeline_id, {"component": BM25, "params": "abc"}
            )

    def test_a_reranker_that_is_not_a_reference_is_rejected(self, orm_db, tmp_path):
        session, _ = _index(orm_db, tmp_path, "malformed_reranker")
        old = _parameters(_bm25(5), None)
        old["query_transformation"]["params"]["reranker"] = "BM25Retriever"

        with pytest.raises(RAGPipelineConfigError, match="reranker"):
            CleanupService(orm_db).cleanup_orphaned_resources(
                session.id, old, _parameters(_bm25(5), None)
            )

    def test_a_reference_without_params_is_the_minimal_reference(
        self, orm_db, tmp_path
    ):
        _, index = _index(orm_db, tmp_path, "minimal_reference")
        bridge = index.sparse(BM25, {})

        matches = CleanupService(orm_db)._matching_bridges(
            index.pipeline_id, {"component": BM25}
        )

        assert [match.id for match in matches] == [bridge]


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


class TestBudgetRejectsMalformedStoredStages:
    """The budget prices what is stored, and fails on a stage it cannot read."""

    def test_an_omitted_cap_and_an_explicit_null_price_the_same_count(self):
        service = _budget_service()
        omitted = {"component": "LLMQueryDecomposer", "params": {}}

        assert service._query_count(omitted) == service._query_count(
            _decomposition(None, None)
        )

    def test_a_disabled_stage_is_a_single_query(self):
        assert _budget_service()._query_count({}) == 1
        assert _budget_service()._query_count(None) == 1

    def test_a_stored_count_that_is_not_a_positive_integer_is_rejected(self):
        for bad in ("3", 0, True):
            with pytest.raises(RAGPipelineConfigError, match="max_subqueries"):
                _budget_service()._query_count(_decomposition(bad, None))

    def test_a_stage_without_a_params_dict_is_rejected(self):
        with pytest.raises(RAGPipelineConfigError, match="no 'params' dict"):
            _budget_service()._query_count({"component": "LLMQueryDecomposer"})

    def test_a_reranker_that_is_not_a_reference_is_rejected(self):
        with pytest.raises(RAGPipelineConfigError, match="not a component reference"):
            _budget_service()._pool_cap(_decomposition(3, "DenseEmbeddingRetriever"))

    def test_a_reranker_with_non_dict_params_is_rejected(self):
        reranker = {"component": "DenseEmbeddingRetriever", "params": "abc"}

        with pytest.raises(RAGPipelineConfigError, match="not a dict"):
            _budget_service()._pool_cap(_decomposition(3, reranker))

    def test_a_reranker_reference_without_params_is_the_minimal_reference(self):
        reranker = {"component": "DenseEmbeddingRetriever"}

        assert _budget_service()._pool_cap(_decomposition(3, reranker)) is not None
