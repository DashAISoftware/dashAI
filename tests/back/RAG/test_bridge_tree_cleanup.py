"""Bridge trees are released top-down, and no composite is left without children.

Invalidating a chunk set deletes the leaves it fitted, every composite built over
them at any depth, and nothing a surviving tree still references. The post-index
release does the same for the stale trees of a session, and a composite that is
set up again over the same children reuses its existing root.
"""

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
)
from DashAI.back.services.RAG.cleanup_service import (
    CleanupService,
    capture_index_footprint,
)
from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService
from DashAI.back.services.RAG.retriever_setup_service import RetrieverSetupService
from tests.back.RAG.conftest import (
    _insert_data_document,
    _insert_rag_session,
    bm25_retriever_params,
)
from tests.back.RAG.test_index_cleanup import (
    COMPOSITE_CLASS,
    DENSE_CLASS,
    EMBEDDINGS_DIR,
    LIVE_K1,
    SPARSE_CLASS,
    SPARSE_DIR,
    _build_index,
    _chunk_set,
    _cleanup,
    _composite,
    _dense_bridge,
    _embedding_model,
    _matrix,
    _pipeline,
    _rag,
    _sparse_bridge,
)
from tests.back.RAG.test_retriever_identity import (
    _EMBEDDING_PARAMS,
    _cache_corpus,
    _dense_params,
    _registry,
)

#: Sparse leaves of the doomed chunk set, fitted with their own weighting.
LEAF_K1 = 1.1
#: Sparse leaves that a surviving tree shares, which must stay intact.
SHARED_K1 = 1.3
#: A sparse leaf added to show that the footprint sees a new bridge.
FOOTPRINT_K1 = 1.7
#: A bridge id that no row uses, for a link that dangles.
MISSING_BRIDGE_ID = 999_998


@dataclass(frozen=True)
class _TwoChunkSets:
    """A pipeline with a doomed chunk set, a live chunk set and a sibling root.

    Attributes
    ----------
    session_id : int
    pipeline_id : int
    document_id : int
    rag : Path
        The RAG storage root the fitted folders live under.
    doomed_set : int
        The chunk set the tests invalidate.
    live_set : int
        A chunk set that is not invalidated.
    sibling_root : int
        A unit sparse root over the live chunk set, which must survive.
    sibling_folder : Path
        The storage folder of the sibling root.
    """

    session_id: int
    pipeline_id: int
    document_id: int
    rag: Path
    doomed_set: int
    live_set: int
    sibling_root: int
    sibling_folder: Path


@dataclass(frozen=True)
class _Fitted:
    """A fitted leaf, with the storage it owns.

    Attributes
    ----------
    bridge_id : int
    folder : Path
        The sparse folder, or the embedding matrix folder of a dense leaf.
    model_id : int | None
        The embedding model of a dense leaf; ``None`` for a sparse leaf.
    """

    bridge_id: int
    folder: Path
    model_id: int | None


def _two_chunk_sets(db: Session, tmp_path: Path) -> _TwoChunkSets:
    """Build a session with a doomed chunk set, a live one and a sibling root."""
    session = _insert_rag_session(db, f"bridge_{uuid.uuid4().hex[:8]}")
    document = _insert_data_document(
        db, tmp_path / "docs", f"{uuid.uuid4().hex[:8]}.txt", ["t"]
    )
    rag = _rag(tmp_path)
    pipeline_id = _pipeline(db, session.id)
    doomed_set = _chunk_set(db, session.id, document.id, rag)
    live_set = _chunk_set(db, session.id, document.id, rag)
    sibling_folder = rag / SPARSE_DIR / "sibling"
    sibling_root = _sparse_bridge(db, pipeline_id, live_set, sibling_folder, LIVE_K1)
    db.commit()
    return _TwoChunkSets(
        session_id=session.id,
        pipeline_id=pipeline_id,
        document_id=document.id,
        rag=rag,
        doomed_set=doomed_set,
        live_set=live_set,
        sibling_root=sibling_root,
        sibling_folder=sibling_folder,
    )


def _sparse_leaf(
    db: Session, scenario: _TwoChunkSets, chunk_set_id: int, label: str, k1: float
) -> _Fitted:
    """Insert a sparse leaf of a chunk set with its own storage folder.

    ``k1`` must differ between the sparse leaves of one chunk set, because the
    table keys a row by its class, parameters and chunk set.
    """
    folder = scenario.rag / SPARSE_DIR / label
    bridge_id = _sparse_bridge(db, scenario.pipeline_id, chunk_set_id, folder, k1)
    return _Fitted(bridge_id=bridge_id, folder=folder, model_id=None)


def _dense_leaf(
    db: Session, scenario: _TwoChunkSets, chunk_set_id: int, label: str
) -> _Fitted:
    """Insert a dense leaf with its embedding model and matrix folder."""
    model_id = _embedding_model(db, label)
    folder = scenario.rag / EMBEDDINGS_DIR / label
    _matrix(db, scenario.document_id, chunk_set_id, model_id, folder)
    bridge_id = _dense_bridge(db, scenario.pipeline_id, chunk_set_id, model_id, label)
    return _Fitted(bridge_id=bridge_id, folder=folder, model_id=model_id)


def _invalidate(db: Session, scenario: _TwoChunkSets, chunk_set_id: int) -> None:
    """Invalidate one chunk set, leaving the commit to the caller."""
    CleanupService(db, rag_path=scenario.rag)._invalidate_chunk_set(chunk_set_id)


def _assert_gone(db: Session, bridge_ids: list[int]) -> None:
    """Every given bridge row must be deleted."""
    for bridge_id in bridge_ids:
        assert db.get(RAGRetriever, bridge_id) is None, f"bridge {bridge_id} remains"


def _assert_sound(db: Session) -> None:
    """No child link dangles, and every composite still has at least one child."""
    bridge_ids = {row[0] for row in db.query(RAGRetriever.id).all()}
    links = db.query(RAGRetrieverChild).all()
    dangling = [
        link.id
        for link in links
        if link.parent_id not in bridge_ids or link.child_id not in bridge_ids
    ]
    assert dangling == [], "child links point at missing bridges"
    parents = {link.parent_id for link in links}
    for bridge in db.query(RAGRetriever).all():
        if bridge.sparse_detail is None and bridge.dense_detail is None:
            assert bridge.id in parents, f"composite {bridge.id} has no children"


def _nest(
    db: Session,
    scenario: _TwoChunkSets,
    innermost: list[int],
    levels: int,
    label: str,
) -> tuple[list[int], list[int]]:
    """Build ``levels`` composites, each wrapping the one below with a new leaf.

    The wrapping leaves belong to the live chunk set, so every composite above
    the first has a child that is not invalidated. That is what leaves a
    grandparent behind when only its direct parent is released.

    Returns the composite ids, innermost first, and the ids of the wrapping
    leaves.
    """
    composites = [_composite(db, scenario.pipeline_id, innermost)]
    wrapping_leaves: list[int] = []
    for level in range(1, levels):
        wrap = _sparse_leaf(
            db,
            scenario,
            scenario.live_set,
            f"{label}_wrap_{level}",
            LEAF_K1 + level,
        )
        wrapping_leaves.append(wrap.bridge_id)
        composites.append(
            _composite(db, scenario.pipeline_id, [composites[-1], wrap.bridge_id])
        )
    return composites, wrapping_leaves


# ===================================================================
# Chunk-set invalidation
# ===================================================================


def test_sparse_leaf_alone_is_released_after_commit(orm_db, tmp_path):
    """A lone sparse leaf goes with its folder, and the sibling root survives."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    leaf = _sparse_leaf(orm_db, scenario, scenario.doomed_set, "alone", LEAF_K1)
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    assert leaf.folder.exists(), "folders must outlive the transaction"
    orm_db.commit()

    _assert_gone(orm_db, [leaf.bridge_id])
    assert not leaf.folder.exists()
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    assert scenario.sibling_folder.exists()
    _assert_sound(orm_db)


def test_dense_leaf_alone_takes_its_matrix_and_model(orm_db, tmp_path):
    """A lone dense leaf goes with its matrix folder and its embedding model."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    leaf = _dense_leaf(orm_db, scenario, scenario.doomed_set, "dense_alone")
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    _assert_gone(orm_db, [leaf.bridge_id])
    assert orm_db.get(RAGEmbeddingModel, leaf.model_id) is None
    assert not leaf.folder.exists()
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    _assert_sound(orm_db)


def test_composite_over_leaves_is_released_with_them(orm_db, tmp_path):
    """A composite over a sparse and a dense leaf goes with both of them."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    sparse = _sparse_leaf(orm_db, scenario, scenario.doomed_set, "over_sparse", LEAF_K1)
    dense = _dense_leaf(orm_db, scenario, scenario.doomed_set, "over_dense")
    top = _composite(orm_db, scenario.pipeline_id, [sparse.bridge_id, dense.bridge_id])
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    _assert_gone(orm_db, [top, sparse.bridge_id, dense.bridge_id])
    assert orm_db.get(RAGEmbeddingModel, dense.model_id) is None
    assert not sparse.folder.exists()
    assert not dense.folder.exists()
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    _assert_sound(orm_db)


@pytest.mark.parametrize("levels", [2, 3], ids=["two_levels", "three_levels"])
def test_nested_composites_over_leaves_leave_no_composite_behind(
    orm_db, tmp_path, levels
):
    """Every composite of a nested chain goes, whatever its depth."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    sparse = _sparse_leaf(
        orm_db, scenario, scenario.doomed_set, "nested_sparse", LEAF_K1
    )
    dense = _dense_leaf(orm_db, scenario, scenario.doomed_set, "nested_dense")
    composites, wrapping_leaves = _nest(
        orm_db,
        scenario,
        [sparse.bridge_id, dense.bridge_id],
        levels,
        "nested",
    )
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    doomed = composites + wrapping_leaves + [sparse.bridge_id, dense.bridge_id]
    _assert_gone(orm_db, doomed)
    assert not sparse.folder.exists()
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    _assert_sound(orm_db)


def test_a_leaf_shared_with_a_surviving_tree_is_kept(orm_db, tmp_path):
    """A live-set leaf that a live composite also uses survives the invalidation."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    shared = _sparse_leaf(orm_db, scenario, scenario.live_set, "shared", SHARED_K1)
    doomed = _sparse_leaf(
        orm_db, scenario, scenario.doomed_set, "shared_doomed", LEAF_K1
    )
    stale_top = _composite(
        orm_db, scenario.pipeline_id, [shared.bridge_id, doomed.bridge_id]
    )
    live_top = _composite(orm_db, scenario.pipeline_id, [shared.bridge_id])
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    _assert_gone(orm_db, [stale_top, doomed.bridge_id])
    assert orm_db.get(RAGRetriever, shared.bridge_id) is not None
    assert shared.folder.exists()
    assert orm_db.get(RAGRetriever, live_top) is not None
    links = [
        (row.parent_id, row.child_id)
        for row in orm_db.query(RAGRetrieverChild).filter_by(parent_id=live_top)
    ]
    assert links == [(live_top, shared.bridge_id)]
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    _assert_sound(orm_db)


# ===================================================================
# Post-index release
# ===================================================================


@pytest.mark.parametrize("levels", [2, 3], ids=["two_levels", "three_levels"])
def test_post_index_release_removes_nested_stale_composites(orm_db, tmp_path, levels):
    """Stale composites nested over stale leaves go; the live tree keeps its leaves."""
    session = _insert_rag_session(orm_db, f"nested_post_{uuid.uuid4().hex[:6]}")
    document = _insert_data_document(
        orm_db, tmp_path / "docs", f"{uuid.uuid4().hex[:6]}.txt", ["p"]
    )
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    stale = [
        _composite(
            orm_db, index.pipeline_id, [index.stale_sparse_id, index.stale_dense_id]
        )
    ]
    for _level in range(1, levels):
        stale.append(
            _composite(orm_db, index.pipeline_id, [stale[-1], index.live_sparse_id])
        )
    orm_db.commit()

    _cleanup(orm_db, index)

    _assert_gone(orm_db, stale + [index.stale_sparse_id, index.stale_dense_id])
    assert not index.stale_sparse_folder.exists()
    assert not index.stale_matrix_folder.exists()
    assert orm_db.get(RAGRetriever, index.root_id) is not None
    assert orm_db.get(RAGRetriever, index.live_sparse_id) is not None
    assert orm_db.get(RAGRetriever, index.live_dense_id) is not None
    assert index.live_sparse_folder.exists()
    _assert_sound(orm_db)


# ===================================================================
# Composite roots are reused by setup
# ===================================================================


def _composite_params(child_k1: float) -> dict[str, Any]:
    """Parameters of a round-robin composite over one BM25 child."""
    child = {**bm25_retriever_params(), "k1": child_k1}
    return {
        "merge_strategy": "round_robin",
        "children": [{"component": SPARSE_CLASS, "params": child}],
    }


def _setup_service(db: Session, client: TestClient, tmp_path: Path):
    """Insert a session with a chunk set and pipeline, and return a setup service.

    Returns the service and the pipeline id, which scopes the row counts.
    """
    session = _insert_rag_session(db, f"reuse_{uuid.uuid4().hex[:6]}")
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session.id
    )
    pipeline = RAGPipeline(session_id=session.id, name="")
    db.add_all([chunk_set, pipeline])
    db.commit()
    service = RetrieverSetupService(
        db,
        _registry(client),
        str(tmp_path),
        _cache_corpus(),
        chunk_set.id,
        pipeline.id,
        "test-chunking",
    )
    return service, pipeline.id


def _count_bridges(db: Session, pipeline_id: int, class_name: str) -> int:
    """Count the bridge rows of one class in one pipeline."""
    return (
        db.query(RAGRetriever)
        .filter_by(pipeline_id=pipeline_id, class_name=class_name)
        .count()
    )


def test_consecutive_setups_of_one_composite_reuse_its_root(orm_db, client, tmp_path):
    """Setting up the same composite twice keeps one root and one child bridge."""
    service, pipeline_id = _setup_service(orm_db, client, tmp_path)
    first = service.setup(COMPOSITE_CLASS, _composite_params(1.5))
    second = service.setup(COMPOSITE_CLASS, _composite_params(1.5))

    assert second.db_record_id == first.db_record_id
    assert _count_bridges(orm_db, pipeline_id, COMPOSITE_CLASS) == 1
    assert _count_bridges(orm_db, pipeline_id, SPARSE_CLASS) == 1


def test_changing_a_child_creates_a_new_composite_root(orm_db, client, tmp_path):
    """A composite over a changed child is a new root; the old one awaits cleanup."""
    service, pipeline_id = _setup_service(orm_db, client, tmp_path)
    first = service.setup(COMPOSITE_CLASS, _composite_params(1.5))
    changed = service.setup(COMPOSITE_CLASS, _composite_params(2.0))

    assert changed.db_record_id != first.db_record_id
    assert _count_bridges(orm_db, pipeline_id, COMPOSITE_CLASS) == 2
    assert _count_bridges(orm_db, pipeline_id, SPARSE_CLASS) == 2


# ===================================================================
# Walking and measuring the trees
# ===================================================================


def test_tree_walk_lists_a_shared_child_once_and_survives_a_cycle(orm_db, tmp_path):
    """A shared child is listed once; a cycle or a dangling link ends the walk."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    shared = _sparse_leaf(orm_db, scenario, scenario.live_set, "walk", SHARED_K1)
    left = _composite(orm_db, scenario.pipeline_id, [shared.bridge_id])
    right = _composite(orm_db, scenario.pipeline_id, [shared.bridge_id])
    top = _composite(orm_db, scenario.pipeline_id, [left, right])
    orm_db.add(
        RAGRetrieverChild(parent_id=right, child_id=MISSING_BRIDGE_ID, child_order=1)
    )
    orm_db.add(
        RAGRetrieverChild(parent_id=shared.bridge_id, child_id=top, child_order=0)
    )
    orm_db.commit()

    order = CleanupService(orm_db, rag_path=scenario.rag)._tree_order([top])

    assert order == [top, left, shared.bridge_id, right, MISSING_BRIDGE_ID]


def test_footprint_is_unchanged_by_a_reuse_and_moves_on_a_new_bridge(orm_db, tmp_path):
    """Footprints match when nothing was added, and differ after a new bridge."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    before = capture_index_footprint(orm_db, scenario.session_id)

    assert capture_index_footprint(orm_db, scenario.session_id) == before

    _sparse_leaf(orm_db, scenario, scenario.live_set, "footprint", FOOTPRINT_K1)
    orm_db.commit()
    after = capture_index_footprint(orm_db, scenario.session_id)

    assert after != before
    assert after.chunk_set_ids == before.chunk_set_ids
    assert len(after.bridge_ids) == len(before.bridge_ids) + 1


# ===================================================================
# Session parameter updates release what the old configuration left
# ===================================================================


def _dense_composite_params() -> dict[str, Any]:
    """Parameters of a round-robin composite over one dense child."""
    child = _dense_params(_EMBEDDING_PARAMS)
    return {
        "merge_strategy": "round_robin",
        "children": [{"component": DENSE_CLASS, "params": child}],
    }


@pytest.mark.parametrize(
    "shared", [False, True], ids=["unshared_model", "shared_model"]
)
def test_composite_switched_to_a_unit_releases_its_dense_leaves(
    orm_db, client, tmp_path, shared
):
    """Dense leaves of a replaced composite release matrices; a shared model stays."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    label = f"cascade_{shared}"
    dense = _dense_leaf(orm_db, scenario, scenario.doomed_set, label)
    composite = _composite(orm_db, scenario.pipeline_id, [dense.bridge_id])
    if shared:
        other = _insert_rag_session(orm_db, f"sharer_{uuid.uuid4().hex[:8]}")
        other_pipeline = _pipeline(orm_db, other.id)
        other_set = _chunk_set(orm_db, other.id, scenario.document_id, scenario.rag)
        _dense_bridge(orm_db, other_pipeline, other_set, dense.model_id, "sharer")
    orm_db.commit()
    old_parameters = {
        "documents": [],
        "retriever_model": {
            "component": COMPOSITE_CLASS,
            "params": _dense_composite_params(),
        },
    }
    new_parameters = {
        "documents": [],
        "retriever_model": {
            "component": SPARSE_CLASS,
            "params": bm25_retriever_params(),
        },
    }

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        scenario.session_id, old_parameters, new_parameters
    )

    _assert_gone(orm_db, [composite, dense.bridge_id])
    matrices = (
        orm_db.query(RAGEmbeddingMatrix)
        .filter_by(chunk_set_id=scenario.doomed_set, embedding_model_id=dense.model_id)
        .count()
    )
    assert matrices == 0
    assert not dense.folder.exists()
    assert (orm_db.get(RAGEmbeddingModel, dense.model_id) is not None) is shared
    assert orm_db.get(RAGRetriever, scenario.sibling_root) is not None
    _assert_sound(orm_db)


def test_unit_cascade_keeps_a_child_of_a_surviving_composite(orm_db, client, tmp_path):
    """A unit bridge that a surviving composite still reads is not deleted."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    child = _sparse_leaf(orm_db, scenario, scenario.live_set, "unit_child", SHARED_K1)
    survivor = _composite(orm_db, scenario.pipeline_id, [child.bridge_id])
    orm_db.commit()
    old_parameters = {
        "documents": [],
        "retriever_model": {
            "component": SPARSE_CLASS,
            "params": bm25_retriever_params(),
        },
    }
    changed = {**bm25_retriever_params(), "k1": 2.5}
    new_parameters = {
        "documents": [],
        "retriever_model": {"component": SPARSE_CLASS, "params": changed},
    }

    CleanupService(orm_db, _registry(client)).cleanup_orphaned_resources(
        scenario.session_id, old_parameters, new_parameters
    )

    assert orm_db.get(RAGRetriever, survivor) is not None
    assert orm_db.get(RAGRetriever, child.bridge_id) is not None
    assert child.folder.exists()
    _assert_sound(orm_db)


def test_invalidation_releases_a_leaf_behind_a_rootless_cycle(orm_db, tmp_path):
    """A leaf that no root reaches is still released with its chunk set."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    other = _insert_rag_session(orm_db, f"cycle_{uuid.uuid4().hex[:8]}")
    cycle_pipeline = _pipeline(orm_db, other.id)
    folder = scenario.rag / SPARSE_DIR / "cycle_leaf"
    leaf_bridge = _sparse_bridge(
        orm_db, cycle_pipeline, scenario.doomed_set, folder, LEAF_K1
    )
    first = _composite(orm_db, cycle_pipeline, [leaf_bridge])
    second = _composite(orm_db, cycle_pipeline, [first])
    orm_db.add(RAGRetrieverChild(parent_id=first, child_id=second, child_order=1))
    orm_db.commit()

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    _assert_gone(orm_db, [leaf_bridge])
    assert not folder.exists()
    assert orm_db.get(RAGRetriever, first) is not None
    assert orm_db.get(RAGRetriever, second) is not None
    _assert_sound(orm_db)


def test_a_bridge_with_a_sparse_and_a_dense_detail_releases_both(orm_db, tmp_path):
    """Both details of one bridge go with it, and no detail is left dangling."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    folder = scenario.rag / SPARSE_DIR / "both"
    bridge_id = _sparse_bridge(
        orm_db, scenario.pipeline_id, scenario.doomed_set, folder, LEAF_K1
    )
    model_id = _embedding_model(orm_db, "both")
    matrix_folder = scenario.rag / EMBEDDINGS_DIR / "both"
    _matrix(orm_db, scenario.document_id, scenario.doomed_set, model_id, matrix_folder)
    dense = RAGDenseRetriever(
        bridge_id=bridge_id,
        chunk_set_id=scenario.doomed_set,
        class_name=DENSE_CLASS,
        parameters={"label": "both"},
        embedding_model_id=model_id,
    )
    orm_db.add(dense)
    orm_db.commit()
    dense_id = dense.id

    _invalidate(orm_db, scenario, scenario.doomed_set)
    orm_db.commit()

    _assert_gone(orm_db, [bridge_id])
    assert orm_db.get(RAGDenseRetriever, dense_id) is None
    assert orm_db.get(RAGEmbeddingModel, model_id) is None
    assert not folder.exists()
    assert not matrix_folder.exists()
    _assert_sound(orm_db)


def test_find_composite_refuses_an_empty_child_list(orm_db, tmp_path):
    """An empty child list names no composite, so it must not match a childless one."""
    scenario = _two_chunk_sets(orm_db, tmp_path)
    _composite(orm_db, scenario.pipeline_id, [])
    orm_db.commit()

    with pytest.raises(ValueError, match="child"):
        RetrieverDBService(orm_db).find_composite(
            COMPOSITE_CLASS, scenario.pipeline_id, []
        )
