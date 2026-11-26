"""The retriever stage and the reranker share one pipeline's rows during cleanup.

The reranker keeps its rows under the retriever's pipeline, and one row serves
both stages when their persistence identities are equal. These tests cover the
combinations the release must get right: the post-index release, a change to
one stage only, a nested reranker composite, and dense matrices read by both.
"""

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import DashAI.back.job.RAG_job as rag_job_module
from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGChunkSet,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence_signature import (
    reference_signature,
)
from DashAI.back.services.RAG import cleanup_service
from DashAI.back.services.RAG.cleanup_service import (
    CleanupService,
    _retriever_identity,
    capture_index_footprint,
    has_stale_index_rows,
    run_post_index_cleanup,
)
from tests.back.RAG.conftest import _insert_data_document, _insert_rag_session
from tests.back.RAG.test_bridge_tree_cleanup import _assert_sound
from tests.back.RAG.test_index_cleanup import (
    EMBEDDINGS_DIR,
    SPARSE_DIR,
    _chunk_set,
    _embedding_model,
    _matrix,
    _pipeline,
    _rag,
    _sparse_bridge,
)
from tests.back.RAG.test_retriever_identity import _registry

BM25 = "BM25Retriever"
DENSE = "DenseEmbeddingRetriever"
EMBEDDING = "AllMiniLML6V2Embedding"
PARALLEL = "ParallelRetriever"
SEQUENTIAL = "SequentialRetriever"
#: Fitted weightings of the sparse rows. ``k1`` is persistent; ``top_k`` is not.
MAIN_K1 = 2.0
RETRIEVER_K1 = 2.5
RERANK_A_K1 = 3.1
RERANK_B_K1 = 3.2
RERANK_C_K1 = 3.3
STALE_K1 = 4.4


@dataclass(frozen=True)
class _Stage:
    """A session's pipeline with one chunk set of a document.

    Attributes
    ----------
    session_id : int
    pipeline_id : int
    document_id : int
    chunk_set_id : int
    rag : Path
        The RAG storage root the fitted folders live under.
    """

    session_id: int
    pipeline_id: int
    document_id: int
    chunk_set_id: int
    rag: Path


def _sparse_ref(k1: float) -> dict[str, Any]:
    """Return a BM25 reference, with ``top_k`` left out as it is query-time."""
    return {"component": BM25, "params": {"k1": k1}}


def _composite_ref(component: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a composite reference over the given child references, in order."""
    return {"component": component, "params": {"children": children}}


def _dense_ref(label: str) -> dict[str, Any]:
    """Return a dense reference whose ``label`` tells two rows of one model apart."""
    return {
        "component": DENSE,
        "params": {
            "embedding_model": {"component": EMBEDDING, "params": {}},
            "label": label,
        },
    }


def _parameters(
    retriever: dict[str, Any], reranker: dict[str, Any] | None
) -> dict[str, Any]:
    """Return session parameters with a retriever and an optional reranker."""
    transformation: dict[str, Any] = {"component": "LLMQueryExpander", "params": {}}
    if reranker is not None:
        transformation["params"]["reranker"] = reranker
    return {
        "documents": [],
        "retriever_model": retriever,
        "query_transformation": transformation,
    }


def _stage(db: Session, tmp_path: Path, label: str) -> _Stage:
    """Insert a session with a pipeline and one chunk set of a document."""
    session = _insert_rag_session(db, f"combo_{label}_{uuid.uuid4().hex[:8]}")
    document = _insert_data_document(
        db, tmp_path / "docs", f"{label}_{uuid.uuid4().hex[:6]}.txt", ["t"]
    )
    rag = _rag(tmp_path)
    pipeline_id = _pipeline(db, session.id)
    chunk_set_id = _chunk_set(db, session.id, document.id, rag)
    db.commit()
    return _Stage(
        session_id=session.id,
        pipeline_id=pipeline_id,
        document_id=document.id,
        chunk_set_id=chunk_set_id,
        rag=rag,
    )


def _leaf(db: Session, stage: _Stage, k1: float, label: str) -> int:
    """Insert a sparse leaf over the stage's chunk set and return its bridge id."""
    return _sparse_bridge(
        db,
        stage.pipeline_id,
        stage.chunk_set_id,
        stage.rag / SPARSE_DIR / f"{label}_{uuid.uuid4().hex[:6]}",
        k1,
    )


def _bridge(db: Session, pipeline_id: int, class_name: str, children: list[int]) -> int:
    """Insert a composite of the given class over the children, in order."""
    parent = RAGRetriever(class_name=class_name, pipeline_id=pipeline_id)
    db.add(parent)
    db.flush()
    for order, child_id in enumerate(children):
        db.add(
            RAGRetrieverChild(parent_id=parent.id, child_id=child_id, child_order=order)
        )
    db.flush()
    return parent.id


def _dense_leaf(db: Session, stage: _Stage, label: str, model_id: int) -> int:
    """Insert a dense leaf whose stored parameters are its reference's signature."""
    bridge = RAGRetriever(class_name=DENSE, pipeline_id=stage.pipeline_id)
    db.add(bridge)
    db.flush()
    db.add(
        RAGDenseRetriever(
            bridge_id=bridge.id,
            chunk_set_id=stage.chunk_set_id,
            class_name=DENSE,
            parameters=_dense_ref(label)["params"],
            embedding_model_id=model_id,
        )
    )
    db.flush()
    return bridge.id


def _set_parameters(db: Session, session_id: int, parameters: dict[str, Any]) -> None:
    """Store the session's parameters, as the post-index cleanup reads them."""
    session = db.get(GenerativeSession, session_id)
    session.parameters = parameters
    db.commit()


def _exists(db: Session, bridge_id: int) -> bool:
    """Whether a bridge row is still in the database."""
    return db.get(RAGRetriever, bridge_id) is not None


# ── Post-index release ───────────────────────────────────────────────────────


def test_post_index_release_keeps_a_row_shared_by_retriever_and_reranker(
    orm_db, tmp_path
):
    """The live reranker root is kept with the retriever's row it shares."""
    stage = _stage(orm_db, tmp_path, "post_shared")
    shared = _leaf(orm_db, stage, RERANK_A_K1, "shared")
    other = _leaf(orm_db, stage, RERANK_B_K1, "other")
    live_root = _bridge(orm_db, stage.pipeline_id, PARALLEL, [shared, other])
    stale_root = _leaf(orm_db, stage, STALE_K1, "stale")
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(
            _composite_ref(
                PARALLEL, [_sparse_ref(RERANK_A_K1), _sparse_ref(RERANK_B_K1)]
            ),
            _sparse_ref(RERANK_A_K1),
        ),
    )

    CleanupService(orm_db, rag_path=stage.rag).cleanup_after_reindex(
        stage.session_id, live_root, shared
    )

    assert _exists(orm_db, live_root)
    assert _exists(orm_db, shared)
    assert _exists(orm_db, other)
    assert not _exists(orm_db, stale_root)
    _assert_sound(orm_db)


def test_post_index_release_without_a_built_reranker_protects_nothing(
    client: TestClient, orm_db, tmp_path
):
    """A stored reranker with no rows protects nothing; the stale root is released."""
    stage = _stage(orm_db, tmp_path, "post_unbuilt")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    stale_root = _leaf(orm_db, stage, STALE_K1, "stale")
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_A_K1)),
    )

    CleanupService(orm_db, _registry(client), rag_path=stage.rag).cleanup_after_reindex(
        stage.session_id, live_root, None
    )

    assert _exists(orm_db, live_root)
    assert not _exists(orm_db, stale_root)
    _assert_sound(orm_db)


def test_post_index_release_refuses_an_unexpected_reranker_root(orm_db, tmp_path):
    """A reranker root the session's parameters do not name is refused as well."""
    stage = _stage(orm_db, tmp_path, "post_unexpected")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    reranker_root = _leaf(orm_db, stage, RERANK_A_K1, "reranker")
    stale_root = _leaf(orm_db, stage, STALE_K1, "stale")
    orm_db.commit()
    _set_parameters(orm_db, stage.session_id, _parameters(_sparse_ref(MAIN_K1), None))

    with pytest.raises(ValueError, match="does not match"):
        CleanupService(orm_db, rag_path=stage.rag).cleanup_after_reindex(
            stage.session_id, live_root, reranker_root
        )

    assert _exists(orm_db, stale_root)


# ── One stage changes ────────────────────────────────────────────────────────


def test_removing_a_nested_reranker_composite_releases_it_top_down(
    client: TestClient, orm_db, tmp_path
):
    """A reranker composite nested in a composite goes with its exclusive leaves."""
    stage = _stage(orm_db, tmp_path, "nested_reranker")
    retriever_leaf = _leaf(orm_db, stage, MAIN_K1, "retriever")
    leaf_a = _leaf(orm_db, stage, RERANK_A_K1, "rerank_a")
    leaf_b = _leaf(orm_db, stage, RERANK_B_K1, "rerank_b")
    leaf_c = _leaf(orm_db, stage, RERANK_C_K1, "rerank_c")
    inner = _bridge(orm_db, stage.pipeline_id, PARALLEL, [leaf_a, leaf_b])
    outer = _bridge(orm_db, stage.pipeline_id, SEQUENTIAL, [inner, leaf_c])
    orm_db.commit()
    reranker = _composite_ref(
        SEQUENTIAL,
        [
            _composite_ref(
                PARALLEL, [_sparse_ref(RERANK_A_K1), _sparse_ref(RERANK_B_K1)]
            ),
            _sparse_ref(RERANK_C_K1),
        ],
    )
    old = _parameters(_sparse_ref(MAIN_K1), reranker)
    new = _parameters(_sparse_ref(MAIN_K1), None)

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    for bridge_id in (outer, inner, leaf_a, leaf_b, leaf_c):
        assert not _exists(orm_db, bridge_id), f"bridge {bridge_id} remains"
    assert _exists(orm_db, retriever_leaf)
    assert orm_db.query(RAGSparseRetriever).count() == 1
    _assert_sound(orm_db)


def test_a_retriever_change_keeps_the_rows_the_reranker_still_uses(
    client: TestClient, orm_db, tmp_path
):
    """The old retriever's row survives when the reranker's composite reads it."""
    stage = _stage(orm_db, tmp_path, "retriever_change")
    shared = _leaf(orm_db, stage, RERANK_A_K1, "shared")
    other = _leaf(orm_db, stage, RERANK_B_K1, "other")
    reranker_root = _bridge(orm_db, stage.pipeline_id, PARALLEL, [shared, other])
    orm_db.commit()
    reranker = _composite_ref(
        PARALLEL, [_sparse_ref(RERANK_A_K1), _sparse_ref(RERANK_B_K1)]
    )
    old = _parameters(_sparse_ref(RERANK_A_K1), reranker)
    new = _parameters(_sparse_ref(RETRIEVER_K1), reranker)

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    assert _exists(orm_db, reranker_root)
    assert _exists(orm_db, shared)
    assert _exists(orm_db, other)
    _assert_sound(orm_db)


def test_changing_only_the_reranker_keeps_the_retriever_leaf(
    client: TestClient, orm_db, tmp_path
):
    """Only the reranker's exclusive rows go; the retriever's own leaf stays."""
    stage = _stage(orm_db, tmp_path, "reranker_only")
    retriever_leaf = _leaf(orm_db, stage, MAIN_K1, "retriever")
    reranker_leaf = _leaf(orm_db, stage, RERANK_A_K1, "reranker")
    orm_db.commit()
    old = _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_A_K1))
    new = _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_B_K1))

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    assert _exists(orm_db, retriever_leaf)
    assert not _exists(orm_db, reranker_leaf)
    assert orm_db.query(RAGSparseRetriever).count() == 1


# ── Dense matrices read by both stages ───────────────────────────────────────


def test_a_retriever_change_keeps_the_matrices_the_reranker_reads(
    client: TestClient, orm_db, tmp_path
):
    """A dense retriever that is replaced leaves the matrices its reranker reads."""
    stage = _stage(orm_db, tmp_path, "dense_retriever_change")
    model = _embedding_model(orm_db, "shared_dense")
    old_retriever = _dense_leaf(orm_db, stage, "retriever", model)
    reranker = _dense_leaf(orm_db, stage, "reranker", model)
    folder = stage.rag / EMBEDDINGS_DIR / "shared_dense"
    _matrix(orm_db, stage.document_id, stage.chunk_set_id, model, folder)
    orm_db.commit()
    old = _parameters(_dense_ref("retriever"), _dense_ref("reranker"))
    new = _parameters(_sparse_ref(RETRIEVER_K1), _dense_ref("reranker"))

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    assert not _exists(orm_db, old_retriever)
    assert _exists(orm_db, reranker)
    assert orm_db.query(RAGEmbeddingMatrix).count() == 1
    assert folder.exists()
    assert orm_db.get(RAGEmbeddingModel, model) is not None


def test_a_reranker_removal_keeps_the_matrices_the_retriever_reads(
    client: TestClient, orm_db, tmp_path
):
    """Removing the reranker releases its rows, not the matrices the retriever reads."""
    stage = _stage(orm_db, tmp_path, "dense_reranker_removed")
    model = _embedding_model(orm_db, "retriever_dense")
    retriever = _dense_leaf(orm_db, stage, "retriever", model)
    reranker = _dense_leaf(orm_db, stage, "reranker", model)
    folder = stage.rag / EMBEDDINGS_DIR / "retriever_dense"
    _matrix(orm_db, stage.document_id, stage.chunk_set_id, model, folder)
    orm_db.commit()
    old = _parameters(_dense_ref("retriever"), _dense_ref("reranker"))
    new = _parameters(_dense_ref("retriever"), None)

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    assert _exists(orm_db, retriever)
    assert not _exists(orm_db, reranker)
    assert orm_db.query(RAGEmbeddingMatrix).count() == 1
    assert folder.exists()
    _assert_sound(orm_db)


# ── The session's reranker, which this index did not build ───────────────────


def _signed_dense_leaf(
    db: Session, stage: _Stage, label: str, model_id: int, registry: Any
) -> int:
    """Insert a dense leaf stored under its reference's persistence signature."""
    signature = reference_signature(_dense_ref(label), registry)
    bridge = RAGRetriever(class_name=DENSE, pipeline_id=stage.pipeline_id)
    db.add(bridge)
    db.flush()
    db.add(
        RAGDenseRetriever(
            bridge_id=bridge.id,
            chunk_set_id=stage.chunk_set_id,
            class_name=DENSE,
            parameters=signature["params"],
            embedding_model_id=model_id,
        )
    )
    db.flush()
    return bridge.id


def _error_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Return the error records the post-index cleanup logged during a test."""
    return [
        record
        for record in caplog.records
        if record.name == cleanup_service.__name__ and record.levelno >= logging.ERROR
    ]


def test_an_unbuilt_reranker_keeps_its_rows_without_an_error(
    client: TestClient, orm_db, tmp_path, caplog
):
    """A reranker this index did not build keeps its current rows, silently."""
    stage = _stage(orm_db, tmp_path, "unbuilt_reranker")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    reranker_root = _leaf(orm_db, stage, RERANK_A_K1, "reranker")
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_A_K1)),
    )

    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        run_post_index_cleanup(
            orm_db, _registry(client), stage.session_id, live_root, stage.rag, None
        )

    assert _exists(orm_db, live_root)
    assert _exists(orm_db, reranker_root)
    assert not _error_records(caplog)
    _assert_sound(orm_db)


def test_an_unbuilt_dense_reranker_keeps_the_matrix_it_reads(
    client: TestClient, orm_db, tmp_path, caplog
):
    """A dense reranker this index did not rebuild keeps the matrix it reads."""
    stage = _stage(orm_db, tmp_path, "unbuilt_dense_reranker")
    model = _embedding_model(orm_db, "unbuilt_reranker_dense")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    reranker = _signed_dense_leaf(orm_db, stage, "reranker", model, _registry(client))
    folder = stage.rag / EMBEDDINGS_DIR / "unbuilt_reranker_dense"
    _matrix(orm_db, stage.document_id, stage.chunk_set_id, model, folder)
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _dense_ref("reranker")),
    )

    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        run_post_index_cleanup(
            orm_db, _registry(client), stage.session_id, live_root, stage.rag, None
        )

    assert _exists(orm_db, reranker)
    assert orm_db.query(RAGEmbeddingMatrix).count() == 1
    assert folder.exists()
    assert not _error_records(caplog)
    _assert_sound(orm_db)


def test_a_reranker_row_the_session_no_longer_names_is_released(
    client: TestClient, orm_db, tmp_path
):
    """Stale reranker rows of another shape go; the named reranker's row stays."""
    stage = _stage(orm_db, tmp_path, "stale_reranker_rows")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    current = _leaf(orm_db, stage, RERANK_B_K1, "current")
    stale = _leaf(orm_db, stage, RERANK_A_K1, "stale")
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_B_K1)),
    )

    CleanupService(orm_db, _registry(client), rag_path=stage.rag).cleanup_after_reindex(
        stage.session_id, live_root, None
    )

    assert _exists(orm_db, live_root)
    assert _exists(orm_db, current)
    assert not _exists(orm_db, stale)
    _assert_sound(orm_db)


def test_a_matching_reranker_on_an_older_chunk_set_is_released(
    client: TestClient, orm_db, tmp_path, caplog
):
    """A reranker tree over an older chunk set is stale, not a violation.

    The reranker is rebuilt on the live chunk set by the next build, so its old
    tree is released with its chunk set rather than kept beside it.
    """
    stage = _stage(orm_db, tmp_path, "older_chunk_reranker")
    live_root = _leaf(orm_db, stage, MAIN_K1, "live")
    older = _chunk_set(orm_db, stage.session_id, stage.document_id, stage.rag)
    older_reranker = _sparse_bridge(
        orm_db,
        stage.pipeline_id,
        older,
        stage.rag / SPARSE_DIR / f"older_reranker_{uuid.uuid4().hex[:6]}",
        RERANK_B_K1,
    )
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_B_K1)),
    )

    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        run_post_index_cleanup(
            orm_db, _registry(client), stage.session_id, live_root, stage.rag, None
        )

    assert _exists(orm_db, live_root)
    assert not _exists(orm_db, older_reranker)
    assert orm_db.get(RAGChunkSet, older) is None
    assert not _error_records(caplog)
    _assert_sound(orm_db)


# ── Stale-row probe and the chat cleanup of a reranker session ───────────────


def _built_pipeline(retriever_id: int, reranker_id: int | None) -> SimpleNamespace:
    """Return the part of a built pipeline the chat cleanup reads."""
    reranker = None
    if reranker_id is not None:
        reranker = SimpleNamespace(get_id=lambda: reranker_id)
    return SimpleNamespace(
        retriever=SimpleNamespace(get_id=lambda: retriever_id),
        query_transformation=SimpleNamespace(reranker=reranker),
    )


def _healthy_reranker_session(client: TestClient, orm_db, tmp_path, label: str):
    """Return a stage whose retriever and reranker each own one root."""
    stage = _stage(orm_db, tmp_path, label)
    retriever_root = _leaf(orm_db, stage, MAIN_K1, "retriever")
    reranker_root = _leaf(orm_db, stage, RERANK_A_K1, "reranker")
    orm_db.commit()
    _set_parameters(
        orm_db,
        stage.session_id,
        _parameters(_sparse_ref(MAIN_K1), _sparse_ref(RERANK_A_K1)),
    )
    return stage, retriever_root, reranker_root


def test_a_healthy_reranker_session_has_no_stale_rows(client, orm_db, tmp_path):
    """The retriever's root and the reranker's root are both expected."""
    stage, _, _ = _healthy_reranker_session(client, orm_db, tmp_path, "probe_ok")

    assert has_stale_index_rows(orm_db, stage.session_id, _registry(client)) is False


def test_a_stray_root_makes_a_reranker_session_stale(client, orm_db, tmp_path):
    """A root that is neither the retriever's nor the reranker's is stale."""
    stage, _, _ = _healthy_reranker_session(client, orm_db, tmp_path, "probe_stray")
    _leaf(orm_db, stage, STALE_K1, "stray")
    orm_db.commit()

    assert has_stale_index_rows(orm_db, stage.session_id, _registry(client)) is True


def test_a_healthy_reranker_session_skips_the_chat_cleanup(
    client, orm_db, tmp_path, monkeypatch
):
    """A chat turn that reuses its index does not clean up a healthy reranker."""
    stage, retriever_root, reranker_root = _healthy_reranker_session(
        client, orm_db, tmp_path, "chat_ok"
    )
    calls: list[tuple] = []
    monkeypatch.setattr(
        rag_job_module, "run_post_index_cleanup", lambda *args: calls.append(args)
    )
    footprint = capture_index_footprint(orm_db, stage.session_id)

    rag_job_module._run_cleanup_if_rebuilt(
        orm_db,
        _registry(client),
        stage.session_id,
        footprint,
        _built_pipeline(retriever_root, reranker_root),
        stage.rag,
    )

    assert calls == []


def test_a_stray_root_makes_the_chat_turn_clean_up(
    client, orm_db, tmp_path, monkeypatch
):
    """A stray root left by a failed cleanup is released by the next chat turn."""
    stage, retriever_root, reranker_root = _healthy_reranker_session(
        client, orm_db, tmp_path, "chat_stray"
    )
    _leaf(orm_db, stage, STALE_K1, "stray")
    orm_db.commit()
    calls: list[tuple] = []
    monkeypatch.setattr(
        rag_job_module, "run_post_index_cleanup", lambda *args: calls.append(args)
    )
    footprint = capture_index_footprint(orm_db, stage.session_id)

    rag_job_module._run_cleanup_if_rebuilt(
        orm_db,
        _registry(client),
        stage.session_id,
        footprint,
        _built_pipeline(retriever_root, reranker_root),
        stage.rag,
    )

    assert len(calls) == 1


# ── Configuration comparisons ────────────────────────────────────────────────


def _signed_sparse_leaf(
    db: Session, stage: _Stage, reference: dict[str, Any], registry: Any, label: str
) -> int:
    """Insert a sparse leaf stored under its reference's persistence signature."""
    bridge_id = _sparse_bridge(
        db, stage.pipeline_id, stage.chunk_set_id, stage.rag / SPARSE_DIR / label, 1.0
    )
    detail = (
        db.query(RAGSparseRetriever)
        .filter(RAGSparseRetriever.bridge_id == bridge_id)
        .one()
    )
    detail.parameters = reference_signature(reference, registry)["params"]
    db.flush()
    return bridge_id


def test_a_minimal_reference_has_the_identity_of_its_explicit_form(client):
    """``{component}`` and ``{component, params: {}}`` name the same retriever."""
    registry = _registry(client)

    assert _retriever_identity({"component": BM25}, registry) == _retriever_identity(
        {"component": BM25, "params": {}}, registry
    )


def test_saving_the_explicit_form_of_a_minimal_reference_keeps_the_retriever(
    client, orm_db, tmp_path
):
    """An update that only spells out the defaults does not release the retriever."""
    registry = _registry(client)
    stage = _stage(orm_db, tmp_path, "minimal_identity")
    explicit = {"component": BM25, "params": {}}
    leaf = _signed_sparse_leaf(orm_db, stage, explicit, registry, "defaults")
    orm_db.commit()
    old = _parameters({"component": BM25}, None)
    new = _parameters(explicit, None)

    CleanupService(orm_db, registry).cleanup_orphaned_resources(
        stage.session_id, old, new
    )

    assert _exists(orm_db, leaf)


def test_a_boolean_fitted_parameter_does_not_match_a_number(orm_db, tmp_path):
    """Configuration equality is strict, so a fitted ``true`` is not ``1``."""
    stage = _stage(orm_db, tmp_path, "strict_match")
    bridge_id = _leaf(orm_db, stage, MAIN_K1, "flag")
    detail = (
        orm_db.query(RAGSparseRetriever)
        .filter(RAGSparseRetriever.bridge_id == bridge_id)
        .one()
    )
    detail.parameters = {"k1": True}
    orm_db.commit()
    bridge = orm_db.get(RAGRetriever, bridge_id)

    matches = CleanupService(orm_db)._bridge_matches(
        bridge, {"component": BM25, "params": {"k1": 1}}
    )

    assert matches is False
