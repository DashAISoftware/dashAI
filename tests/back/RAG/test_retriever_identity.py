"""Tests pinning the retrieve-then-expand options as post-processing knobs.

The two options never change what is indexed nor which stored model a
configuration resolves to. These tests pin the consequences: the sparse storage
hash, the cleanup decision, the preset match and the context budget all treat
them as such, while the budget still pays for the extra chunk text they add.
A cached retriever is loaded with the options the caller asked for even though
the cache key ignores them.
"""

import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    ENABLE_FIELD,
    WINDOW_FIELD,
    strip_expansion_options,
)
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever
from DashAI.back.services.RAG import retriever_presets
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.retriever_setup_service import RetrieverSetupService
from DashAI.back.services.RAG.session_configuration_service import (
    SessionConfigurationService,
)
from tests.back.RAG.conftest import _insert_rag_session, bm25_retriever_params

ENABLED_PARAMS = {ENABLE_FIELD: True, WINDOW_FIELD: 5}


def _registry(client: TestClient):
    """Return the application's component registry."""
    return client.app.container["component_registry"]


def _preset(client: TestClient, key: str) -> Dict[str, Any]:
    """Return one preset recipe resolved against the application registry."""
    presets = retriever_presets.get_retriever_presets(5, _registry(client))
    for preset in presets:
        if preset["key"] == key:
            return preset
    raise AssertionError(f"preset {key} is missing")


def _setup_service(
    db,
    chunks: Dict[int, Dict[int, Chunk]] | None = None,
    chunk_set_id: int = 7,
    chunking_key: str = "test-chunking",
) -> RetrieverSetupService:
    """Return a setup service with the minimal wiring the artifact hash needs."""
    return RetrieverSetupService(
        db=db,
        registry={},
        env_RAG_path="rag-root",
        chunks=chunks or {},
        chunk_set_id=chunk_set_id,
        pipeline_id=1,
        chunking_key=chunking_key,
    )


def _artifact_corpus(text: str = "alpha beta") -> Dict[int, Dict[int, Chunk]]:
    """Build a one-document corpus for the artifact-identity tests."""
    return {1: {0: Chunk(id=1, document_id=1, document_position=0, text=text)}}


# ── Sparse storage identity ──────────────────────────────────────────────────


def test_sparse_storage_folder_ignores_the_expansion_options(orm_db):
    """Toggling expansion reuses the fitted sparse index instead of re-fitting."""
    service = _setup_service(orm_db)
    params = bm25_retriever_params()

    plain = service._build_sparse_persistence_for(BM25Retriever, params)
    enabled = service._build_sparse_persistence_for(
        BM25Retriever, {**params, **ENABLED_PARAMS}
    )

    assert plain.model_dir == enabled.model_dir


def test_sparse_storage_folder_ignores_nested_expansion_options(orm_db):
    """Options on a nested child ref do not change the storage folder."""
    service = _setup_service(orm_db)
    params = bm25_retriever_params()
    legacy = {
        **params,
        "children": [{"component": "BM25Retriever", "params": dict(params)}],
    }
    configured = {
        **params,
        "children": [
            {"component": "BM25Retriever", "params": {**params, **ENABLED_PARAMS}}
        ],
    }

    plain = service._build_sparse_persistence_for(BM25Retriever, legacy)
    nested = service._build_sparse_persistence_for(BM25Retriever, configured)

    assert plain.model_dir == nested.model_dir


def test_sparse_storage_folder_is_shared_across_chunk_sets(orm_db):
    """The same corpus and fitted configuration resolve to one folder."""
    params = bm25_retriever_params()
    chunks = _artifact_corpus()

    first = _setup_service(orm_db, chunks=chunks, chunk_set_id=7)
    second = _setup_service(orm_db, chunks=chunks, chunk_set_id=41)

    first_folder = first._build_sparse_persistence_for(BM25Retriever, params)
    second_folder = second._build_sparse_persistence_for(BM25Retriever, params)

    assert first_folder.model_dir == second_folder.model_dir


def test_sparse_storage_folder_changes_with_the_corpus(orm_db):
    """Different chunk content must never share fitted state."""
    params = bm25_retriever_params()

    first = _setup_service(orm_db, chunks=_artifact_corpus("alpha beta"))
    second = _setup_service(orm_db, chunks=_artifact_corpus("gamma delta"))

    assert (
        first._build_sparse_persistence_for(BM25Retriever, params).model_dir
        != second._build_sparse_persistence_for(BM25Retriever, params).model_dir
    )


def test_sparse_storage_folder_ignores_query_time_parameters(orm_db):
    """``top_k`` and the expansion options never shape the fitted matrix."""
    chunks = _artifact_corpus()
    service = _setup_service(orm_db, chunks=chunks)
    params = bm25_retriever_params()

    base = service._build_sparse_persistence_for(BM25Retriever, params)
    retuned = service._build_sparse_persistence_for(
        BM25Retriever, {**params, "top_k": 9, **ENABLED_PARAMS}
    )

    assert base.model_dir == retuned.model_dir


def test_sparse_storage_folder_changes_with_the_chunking_configuration(orm_db):
    """Different chunking gets its own folder even for identical chunks."""
    chunks = _artifact_corpus()
    params = bm25_retriever_params()

    first = _setup_service(orm_db, chunks=chunks, chunking_key="chunking-a")
    second = _setup_service(orm_db, chunks=chunks, chunking_key="chunking-b")

    assert (
        first._build_sparse_persistence_for(BM25Retriever, params).model_dir
        != second._build_sparse_persistence_for(BM25Retriever, params).model_dir
    )


def test_sparse_storage_folder_still_tracks_a_fitted_parameter(orm_db):
    """The control: a real parameter change does move the storage folder."""
    service = _setup_service(orm_db, chunks=_artifact_corpus())
    params = bm25_retriever_params()

    plain = service._build_sparse_persistence_for(BM25Retriever, params)
    changed = service._build_sparse_persistence_for(
        BM25Retriever, {**params, "k1": 2.0}
    )

    assert plain.model_dir != changed.model_dir


# ── Dense matrix identity ────────────────────────────────────────────────────


def test_dense_matrix_dirs_are_shared_across_chunk_sets(orm_db):
    """The same document content and embedding model share matrix folders."""
    chunks = _artifact_corpus()

    first = _setup_service(orm_db, chunks=chunks, chunk_set_id=7)
    second = _setup_service(orm_db, chunks=chunks, chunk_set_id=41)

    assert (
        first._build_dense_persistence(5).matrix_dirs
        == second._build_dense_persistence(5).matrix_dirs
    )


def test_dense_matrix_dirs_change_with_the_chunking_configuration(orm_db):
    """Different chunking gets its own embedding folder, even for equal chunks."""
    chunks = _artifact_corpus()

    first = _setup_service(orm_db, chunks=chunks, chunking_key="chunking-a")
    second = _setup_service(orm_db, chunks=chunks, chunking_key="chunking-b")

    assert (
        first._build_dense_persistence(5).matrix_dirs
        != second._build_dense_persistence(5).matrix_dirs
    )


def test_dense_matrix_dirs_change_with_the_document_content(orm_db):
    """Different content must never reuse an embedding matrix."""
    first = _setup_service(orm_db, chunks=_artifact_corpus("alpha beta"))
    second = _setup_service(orm_db, chunks=_artifact_corpus("gamma delta"))

    assert (
        first._build_dense_persistence(5).matrix_dirs
        != second._build_dense_persistence(5).matrix_dirs
    )


# ── Cleanup decision ─────────────────────────────────────────────────────────


def _sparse_retriever_state(db, session_id: int, tmp_path, params: Dict[str, Any]):
    """Insert a session pipeline with one fitted sparse retriever."""
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.flush()
    pipeline = RAGPipeline(session_id=session_id, name="")
    db.add(pipeline)
    db.flush()
    bridge = RAGRetriever(class_name="BM25Retriever", pipeline_id=pipeline.id)
    db.add(bridge)
    db.flush()
    folder = tmp_path / f"sparse_{uuid.uuid4().hex[:6]}"
    folder.mkdir(parents=True)
    detail = RAGSparseRetriever(
        bridge_id=bridge.id,
        chunk_set_id=chunk_set.id,
        class_name="BM25Retriever",
        parameters=params,
        storage_folder=str(folder),
    )
    db.add(detail)
    db.commit()
    return bridge, detail, folder


def _composite_retriever_state(db, session_id: int, tmp_path, params: Dict[str, Any]):
    """Insert a session pipeline with a composite retriever and one child."""
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.flush()
    pipeline = RAGPipeline(session_id=session_id, name="")
    db.add(pipeline)
    db.flush()
    child_bridge = RAGRetriever(class_name="BM25Retriever", pipeline_id=pipeline.id)
    db.add(child_bridge)
    db.flush()
    folder = tmp_path / f"sparse_{uuid.uuid4().hex[:6]}"
    folder.mkdir(parents=True)
    child_detail = RAGSparseRetriever(
        bridge_id=child_bridge.id,
        chunk_set_id=chunk_set.id,
        class_name="BM25Retriever",
        parameters=params,
        storage_folder=str(folder),
    )
    db.add(child_detail)
    parent = RAGRetriever(class_name="ParallelRetriever", pipeline_id=pipeline.id)
    db.add(parent)
    db.flush()
    db.add(
        RAGRetrieverChild(parent_id=parent.id, child_id=child_bridge.id, child_order=0)
    )
    db.commit()
    return parent, child_bridge, folder


def test_toggling_expansion_options_does_not_delete_a_unit_retriever(
    client: TestClient, tmp_path
):
    """A session that only toggled the options keeps its fitted retriever."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(db, f"identity_unit_{uuid.uuid4().hex[:6]}").id
        params = bm25_retriever_params()
        bridge, detail, folder = _sparse_retriever_state(
            db, session_id, tmp_path, params
        )
        old_parameters = {
            "documents": [],
            "retriever_model": {"component": "BM25Retriever", "params": params},
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "BM25Retriever",
                "params": {**params, **ENABLED_PARAMS},
            },
        }

        CleanupService(db).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is not None
        assert db.get(RAGSparseRetriever, detail.id) is not None
        assert folder.exists()


def test_changing_a_fitted_parameter_does_delete_the_unit_retriever(
    client: TestClient, tmp_path
):
    """The control: a real parameter change still triggers the cleanup."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_unit_ctl_{uuid.uuid4().hex[:6]}"
        ).id
        params = bm25_retriever_params()
        bridge, _, _ = _sparse_retriever_state(db, session_id, tmp_path, params)
        old_parameters = {
            "documents": [],
            "retriever_model": {"component": "BM25Retriever", "params": params},
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "BM25Retriever",
                "params": {**params, "k1": 2.0},
            },
        }

        CleanupService(db).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is None


def test_toggling_expansion_options_does_not_delete_a_composite_retriever(
    client: TestClient, tmp_path
):
    """A composite keeps its bridge and its children when only options change."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(db, f"identity_comp_{uuid.uuid4().hex[:6]}").id
        child_params = bm25_retriever_params()
        parent, child_bridge, folder = _composite_retriever_state(
            db, session_id, tmp_path, child_params
        )
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "ParallelRetriever",
                "params": {
                    "merge_strategy": "round_robin",
                    "children": [
                        {"component": "BM25Retriever", "params": child_params}
                    ],
                },
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "ParallelRetriever",
                "params": {
                    "merge_strategy": "round_robin",
                    **ENABLED_PARAMS,
                    "children": [
                        {
                            "component": "BM25Retriever",
                            "params": {**child_params, **ENABLED_PARAMS},
                        }
                    ],
                },
            },
        }

        CleanupService(db).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, parent.id) is not None
        assert db.get(RAGRetriever, child_bridge.id) is not None
        assert folder.exists()


# ── Preset matching ──────────────────────────────────────────────────────────


def test_legacy_recipe_without_the_options_matches_its_preset(client: TestClient):
    """A session stored before the options existed still matches its preset."""
    preset = _preset(client, retriever_presets.KEYWORD_PRESET_KEY)
    legacy = strip_expansion_options(preset["params"])

    assert ENABLE_FIELD not in legacy
    assert WINDOW_FIELD not in legacy
    assert (
        retriever_presets.match_preset_key(
            preset["component"], legacy, _registry(client)
        )
        == retriever_presets.KEYWORD_PRESET_KEY
    )


def test_recipe_with_the_options_set_matches_its_preset(client: TestClient):
    """Explicit (even non-default) options do not make a preset look custom."""
    preset = _preset(client, retriever_presets.KEYWORD_PRESET_KEY)
    configured = {**preset["params"], ENABLE_FIELD: True, WINDOW_FIELD: 7}

    assert (
        retriever_presets.match_preset_key(
            preset["component"], configured, _registry(client)
        )
        == retriever_presets.KEYWORD_PRESET_KEY
    )


def test_nested_options_do_not_break_a_composite_preset_match(client: TestClient):
    """Options at the parent and on a child leave the hybrid preset matching."""
    preset = _preset(client, retriever_presets.HYBRID_PRESET_KEY)
    legacy = strip_expansion_options(preset["params"])
    children = []
    for index, child in enumerate(legacy["children"]):
        child_params = dict(child["params"])
        if index == 0:
            child_params.update(ENABLED_PARAMS)
        children.append({"component": child["component"], "params": child_params})
    configured = {**legacy, "children": children, **ENABLED_PARAMS}

    assert (
        retriever_presets.match_preset_key(
            preset["component"], configured, _registry(client)
        )
        == retriever_presets.HYBRID_PRESET_KEY
    )


# ── Effective chunk count ────────────────────────────────────────────────────


def test_effective_chunk_count_is_top_k_without_expansion():
    """A plain leaf costs its configured top-k."""
    assert retriever_presets.effective_chunk_count("BM25Retriever", {"top_k": 5}) == 5
    assert (
        retriever_presets.effective_chunk_count(
            "BM25Retriever", {"top_k": 5, ENABLE_FIELD: False, WINDOW_FIELD: 8}
        )
        == 5
    )


def test_effective_chunk_count_multiplies_by_the_window():
    """An expanded leaf costs one window per returned chunk."""
    params = {"top_k": 5, ENABLE_FIELD: True, WINDOW_FIELD: 4}

    assert retriever_presets.effective_chunk_count("BM25Retriever", params) == 20


def test_effective_chunk_count_ignores_a_window_of_one():
    """A window of one adds no context, so it multiplies by one."""
    params = {"top_k": 5, ENABLE_FIELD: True, WINDOW_FIELD: 1}

    assert retriever_presets.effective_chunk_count("BM25Retriever", params) == 5


def test_effective_chunk_count_sums_composite_children():
    """A composite without its own cap adds up its expansion-aware children."""
    params = {
        "children": [
            {
                "component": "BM25Retriever",
                "params": {"top_k": 4, ENABLE_FIELD: True, WINDOW_FIELD: 3},
            },
            {"component": "DenseEmbeddingRetriever", "params": {"top_k": 2}},
        ]
    }

    assert retriever_presets.effective_chunk_count("ParallelRetriever", params) == 14


def test_effective_chunk_count_caps_an_llm_evaluated_composite():
    """``max_chunks`` caps the pool, and the parent's window multiplies it."""
    children = [{"component": "BM25Retriever", "params": {"top_k": 20}}]
    capped = {"max_chunks": 5, "children": children}
    expanded = {**capped, ENABLE_FIELD: True, WINDOW_FIELD: 3}

    assert (
        retriever_presets.effective_chunk_count("LLMEvaluatedDepthRetriever", capped)
        == 5
    )
    assert (
        retriever_presets.effective_chunk_count("LLMEvaluatedDepthRetriever", expanded)
        == 15
    )


def test_effective_chunk_count_prices_a_capped_parent_with_expanded_children():
    """A cap over an expanded child carries the child's window, not one chunk."""
    params = {
        "top_k": 5,
        "children": [
            {
                "component": "BM25Retriever",
                "params": {"top_k": 20, ENABLE_FIELD: True, WINDOW_FIELD: 3},
            }
        ],
    }

    assert (
        retriever_presets.effective_chunk_count(
            "SentenceTransformerCrossEncoderRetriever", params
        )
        == 15
    )


def test_effective_chunk_count_keeps_a_plain_child_under_a_cap_unchanged():
    """The control: a capped parent over plain children still costs its ``top_k``."""
    params = {
        "top_k": 5,
        "children": [{"component": "BM25Retriever", "params": {"top_k": 20}}],
    }

    assert retriever_presets.effective_chunk_count("MMRRerankerRetriever", params) == 5


def test_effective_chunk_count_does_not_double_apply_the_subtree_factor():
    """A non-capped composite counts its children once, not squared."""
    params = {
        "children": [
            {
                "component": "BM25Retriever",
                "params": {"top_k": 4, ENABLE_FIELD: True, WINDOW_FIELD: 3},
            }
        ],
    }

    assert retriever_presets.effective_chunk_count("ParallelRetriever", params) == 12


# ── Context budget ───────────────────────────────────────────────────────────


def _budget_inputs() -> "tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]":
    """Return the chunking, prompt and generation refs the budget needs."""
    chunking = {"component": "CharacterChunkModel", "params": {"chunk_size": 400}}
    prompt = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"template": "Answer briefly."},
    }
    generation = {
        "component": "Qwen25_15BInstruct",
        "params": {"context_window": 8192, "max_tokens": 512},
    }
    return chunking, prompt, generation


def test_context_budget_grows_when_expansion_is_enabled():
    """The budget pays for the extra chunk text a window adds."""
    service = SessionConfigurationService(db=None, registry={})
    chunking, prompt, generation = _budget_inputs()
    plain = {"component": "BM25Retriever", "params": {"top_k": 4}}
    expanded = {
        "component": "BM25Retriever",
        "params": {"top_k": 4, ENABLE_FIELD: True, WINDOW_FIELD: 3},
    }

    off = service._context_budget(chunking, plain, prompt, generation)
    on = service._context_budget(chunking, expanded, prompt, generation)

    assert off["used_by_chunks"] > 0
    assert on["used_by_chunks"] == off["used_by_chunks"] * 3
    assert on["available"] < off["available"]


@pytest.mark.parametrize("window", [1, 2, 3])
def test_context_budget_matches_the_effective_chunk_count(window):
    """``used_by_chunks`` is the chunk cost times the effective chunk count."""
    service = SessionConfigurationService(db=None, registry={})
    chunking, prompt, generation = _budget_inputs()
    params = {"top_k": 6, ENABLE_FIELD: True, WINDOW_FIELD: window}
    retriever = {"component": "BM25Retriever", "params": params}

    budget = service._context_budget(chunking, retriever, prompt, generation)

    expected = service._chunk_tokens(
        chunking
    ) * retriever_presets.effective_chunk_count("BM25Retriever", params)
    assert budget["used_by_chunks"] == expected


def test_context_budget_prices_a_capped_parent_with_expanded_children():
    """A reranker's budget pays for its expanded child's window."""
    service = SessionConfigurationService(db=None, registry={})
    chunking, prompt, generation = _budget_inputs()
    retriever = {
        "component": "SentenceTransformerCrossEncoderRetriever",
        "params": {
            "top_k": 5,
            "children": [
                {
                    "component": "BM25Retriever",
                    "params": {"top_k": 20, ENABLE_FIELD: True, WINDOW_FIELD: 3},
                }
            ],
        },
    }

    budget = service._context_budget(chunking, retriever, prompt, generation)

    assert budget["used_by_chunks"] == service._chunk_tokens(chunking) * 15


# ── Cache hit keeps the options on the live model ────────────────────────────

CACHE_CORPUS_SIZE = 10


def _cache_corpus() -> Dict[int, Dict[int, Chunk]]:
    """Build ``{document_id: {position: Chunk}}`` with ``c<position>`` texts."""
    chunks: Dict[int, Chunk] = {}
    for position in range(CACHE_CORPUS_SIZE):
        chunks[position] = Chunk(
            id=100 + position,
            document_id=1,
            document_position=position,
            text=f"c{position}",
            page=position + 1,
        )
    return {1: chunks}


def test_cache_hit_keeps_the_expansion_options_on_the_live_model(
    client: TestClient, tmp_path
):
    """The identity ignores the options; the cached model still honours them."""
    registry = _registry(client)
    session_factory = client.app.container["session_factory"]
    params = {**bm25_retriever_params(), "top_k": 1}
    corpus = _cache_corpus()

    with session_factory() as db:
        session = _insert_rag_session(db, f"cache_hit_{uuid.uuid4().hex[:6]}")
        chunk_set = RAGChunkSet(
            signature=uuid.uuid4().hex, parameters={}, session_id=session.id
        )
        db.add(chunk_set)
        pipeline = RAGPipeline(session_id=session.id, name="")
        db.add(pipeline)
        db.commit()
        service = RetrieverSetupService(
            db,
            registry,
            str(tmp_path),
            corpus,
            chunk_set.id,
            pipeline.id,
            "test-chunking",
        )

        plain = service.setup("BM25Retriever", dict(params))
        expanded = service.setup(
            "BM25Retriever", {**params, ENABLE_FIELD: True, WINDOW_FIELD: 3}
        )

        assert expanded.db_record_id == plain.db_record_id
        assert plain.model.enable_retrieve_then_expand is False
        assert expanded.model.enable_retrieve_then_expand is True
        assert expanded.model.expand_window == 3
        assert expanded.model.persistence.model_dir == plain.model.persistence.model_dir

        retrieved, trace = expanded.model.retrieve("c3")

        assert len(retrieved) == 1
        assert retrieved[0].document_position == 2
        assert retrieved[0].source_positions == (2, 3, 4)
        assert trace["chunks"] == ["1_2"]
