"""Tests pinning the retrieve-then-expand options as post-processing knobs.

The two options never change what is indexed nor which stored model a
configuration resolves to. These tests pin the consequences: the sparse storage
hash, the cleanup decision and the context budget all treat them as such, while
the budget still pays for the extra chunk text they add. The preset match is the
one deliberate exception: it compares the options strictly, so a configuration
that sets or omits them differently is custom. A cached retriever is loaded with
the options the caller asked for even though the cache key ignores them.
"""

import copy
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from DashAI.back.converters.hugging_face.text_embedding.base import (
    BATCH_SIZE_FIELD,
    DEVICE_FIELD,
)
from DashAI.back.converters.hugging_face.text_embedding.e5_mistral_gguf import (
    E5MistralGGUFEmbedding,
)
from DashAI.back.converters.hugging_face.text_embedding.sentence_transformer import (
    AllMiniLML6V2Embedding,
)
from DashAI.back.converters.hugging_face.text_embedding.transformer import (
    DistilBERTEmbedding,
)
from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter
from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGDenseRetriever,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import RAGComponentNotFoundError
from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
    MMRRerankerRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.parallel_retriever import (
    ParallelRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence_signature import (
    persistence_signature,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND,
    DEFAULT_EXPAND_WINDOW,
    ENABLE_FIELD,
    TOP_K_FIELD,
    WINDOW_FIELD,
    strip_expansion_options,
)
from DashAI.back.models.RAG.retrievers.similarity import CosineSimilarity
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever
from DashAI.back.services.RAG import retriever_presets
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.index_status_service import IndexStatusService
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


#: Just the classes the artifact-identity tests nest inside BM25 parameters.
_REGISTRY = {
    "BagOfWordsConverter": {"class": BagOfWordsConverter},
    "CosineSimilarity": {"class": CosineSimilarity},
    "BM25Retriever": {"class": BM25Retriever},
}


def _setup_service(
    db,
    chunks: Dict[int, Dict[int, Chunk]] | None = None,
    chunk_set_id: int = 7,
    chunking_key: str = "test-chunking",
    env_rag_path: str = "rag-root",
) -> RetrieverSetupService:
    """Return a setup service with the minimal wiring the artifact hash needs."""
    return RetrieverSetupService(
        db=db,
        registry=_REGISTRY,
        env_RAG_path=env_rag_path,
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


def _write_matrix(folder) -> None:
    """Leave an ``embeddings.npy`` in *folder*, as an indexing job does."""
    import numpy as np

    folder.mkdir(parents=True)
    np.save(folder / "embeddings.npy", np.zeros((1, 3)))


def _legacy_dir(root, chunk_set_id: int = 7):
    """The folder of document 1's matrix before folders were content-addressed."""
    name = f"doc_id-1__chunk_set_id-{chunk_set_id}__embedding_model_id-5"
    return root / "embeddings" / name


def test_a_matrix_indexed_before_content_folders_is_reused(orm_db, tmp_path):
    """A session indexed on an older version keeps reading its own matrix."""
    _write_matrix(_legacy_dir(tmp_path))
    service = _setup_service(
        orm_db, chunks=_artifact_corpus(), env_rag_path=str(tmp_path)
    )

    assert service._build_dense_persistence(5).matrix_dirs[1] == str(
        _legacy_dir(tmp_path)
    )


def test_the_content_folder_wins_over_an_older_one(orm_db, tmp_path):
    """Once the content folder has a matrix, the older folder is not read."""
    service = _setup_service(
        orm_db, chunks=_artifact_corpus(), env_rag_path=str(tmp_path)
    )
    content_dir = service._build_dense_persistence(5).matrix_dirs[1]
    _write_matrix(Path(content_dir))
    _write_matrix(_legacy_dir(tmp_path))

    assert service._build_dense_persistence(5).matrix_dirs[1] == content_dir


def test_an_older_matrix_of_another_chunk_set_is_not_reused(orm_db, tmp_path):
    """Another chunk set may have chunked the document differently."""
    _write_matrix(_legacy_dir(tmp_path, chunk_set_id=41))
    service = _setup_service(
        orm_db, chunks=_artifact_corpus(), chunk_set_id=7, env_rag_path=str(tmp_path)
    )

    assert "__content-" in service._build_dense_persistence(5).matrix_dirs[1]


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


def _composite_retriever_state(
    db,
    session_id: int,
    tmp_path,
    params: Dict[str, Any],
    parent_class: str = "ParallelRetriever",
):
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
    parent = RAGRetriever(class_name=parent_class, pipeline_id=pipeline.id)
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

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
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

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
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

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, parent.id) is not None
        assert db.get(RAGRetriever, child_bridge.id) is not None
        assert folder.exists()


# ── Preset matching ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "key",
    [retriever_presets.KEYWORD_PRESET_KEY, retriever_presets.HYBRID_PRESET_KEY],
)
def test_legacy_recipe_without_the_options_is_custom(client: TestClient, key: str):
    """A session stored before the options existed counts as custom, by design."""
    preset = _preset(client, key)
    legacy = strip_expansion_options(preset["params"])

    assert ENABLE_FIELD not in legacy
    assert WINDOW_FIELD not in legacy
    assert (
        retriever_presets.match_preset_key(
            preset["component"], legacy, _registry(client)
        )
        is None
    )


def _with_top_k(params: Dict[str, Any], top_k: int) -> Dict[str, Any]:
    """Return *params* with ``top_k`` set at the parent and on every child."""
    retuned = {**params, TOP_K_FIELD: top_k}
    if "children" in params:
        retuned["children"] = [
            {**child, "params": _with_top_k(child["params"], top_k)}
            for child in params["children"]
        ]
    return retuned


def test_recipe_with_the_options_set_to_other_values_is_custom(client: TestClient):
    """Enabling expansion or changing its window makes the configuration custom."""
    preset = _preset(client, retriever_presets.KEYWORD_PRESET_KEY)

    enabled = {**preset["params"], ENABLE_FIELD: True}
    widened = {**preset["params"], WINDOW_FIELD: 7}

    assert (
        retriever_presets.match_preset_key(
            preset["component"], enabled, _registry(client)
        )
        is None
    )
    assert (
        retriever_presets.match_preset_key(
            preset["component"], widened, _registry(client)
        )
        is None
    )


def test_recipe_with_the_options_set_to_their_defaults_matches_its_preset(
    client: TestClient,
):
    """Explicitly stating the default options still matches the preset."""
    preset = _preset(client, retriever_presets.KEYWORD_PRESET_KEY)
    configured = {
        **preset["params"],
        ENABLE_FIELD: DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND,
        WINDOW_FIELD: DEFAULT_EXPAND_WINDOW,
    }

    assert (
        retriever_presets.match_preset_key(
            preset["component"], configured, _registry(client)
        )
        == retriever_presets.KEYWORD_PRESET_KEY
    )


def test_options_on_the_parent_or_a_child_make_a_composite_custom(client: TestClient):
    """Expansion on the composite or on one child is a custom configuration."""
    preset = _preset(client, retriever_presets.HYBRID_PRESET_KEY)
    first, *rest = preset["params"]["children"]
    on_parent = {**preset["params"], **ENABLED_PARAMS}
    on_child = {
        **preset["params"],
        "children": [
            {**first, "params": {**first["params"], **ENABLED_PARAMS}},
            *rest,
        ],
    }

    for configured in (on_parent, on_child):
        assert (
            retriever_presets.match_preset_key(
                preset["component"], configured, _registry(client)
            )
            is None
        )


@pytest.mark.parametrize(
    "key",
    [retriever_presets.KEYWORD_PRESET_KEY, retriever_presets.HYBRID_PRESET_KEY],
)
def test_a_different_top_k_alone_keeps_the_preset(client: TestClient, key: str):
    """Moving the Top-K slider never turns a preset into a custom configuration."""
    preset = _preset(client, key)

    assert (
        retriever_presets.match_preset_key(
            preset["component"], _with_top_k(preset["params"], 3), _registry(client)
        )
        == key
    )


def test_a_different_similarity_metric_makes_the_semantic_config_custom(
    client: TestClient,
):
    """The similarity metric decides the preset, so a change is a custom config."""
    preset = _preset(client, retriever_presets.SEMANTIC_PRESET_KEY)
    euclidean = {
        **preset["params"],
        "similarity_metric": {"component": "EuclideanSimilarity", "params": {}},
    }

    assert (
        retriever_presets.match_preset_key(
            preset["component"], euclidean, _registry(client)
        )
        is None
    )


def test_a_different_batch_size_makes_the_semantic_config_custom(client: TestClient):
    """The preset match is strict: a batch size other than the recipe's is custom."""
    preset = _preset(client, retriever_presets.SEMANTIC_PRESET_KEY)

    assert (
        retriever_presets.match_preset_key(
            preset["component"],
            _with_batch_size(preset["params"], 8),
            _registry(client),
        )
        is None
    )


def test_a_different_device_makes_the_semantic_config_custom(client: TestClient):
    """The preset match is strict on the device: another device is a custom config."""
    preset = _preset(client, retriever_presets.SEMANTIC_PRESET_KEY)
    recipe_device = preset["params"]["embedding_model"]["params"][DEVICE_FIELD]

    assert recipe_device != _GPU_DEVICE
    assert (
        retriever_presets.match_preset_key(
            preset["component"], preset["params"], _registry(client)
        )
        == retriever_presets.SEMANTIC_PRESET_KEY
    )
    assert (
        retriever_presets.match_preset_key(
            preset["component"],
            _with_device(preset["params"], _GPU_DEVICE),
            _registry(client),
        )
        is None
    )


@pytest.mark.parametrize(
    "children",
    [
        "junk",
        ["junk"],
        [{"component": "BM25Retriever", "params": "lowercase"}],
    ],
)
def test_malformed_children_raise_a_value_error(client: TestClient, children):
    """Children that are not well-formed refs raise instead of being tolerated."""
    preset = _preset(client, retriever_presets.HYBRID_PRESET_KEY)
    malformed = {**preset["params"], "children": children}

    with pytest.raises(ValueError, match="children"):
        retriever_presets.match_preset_key(
            preset["component"], malformed, _registry(client)
        )


def test_matching_does_not_mutate_the_stored_params(client: TestClient):
    """Normalizing for the match works on copies of the stored configuration."""
    preset = _preset(client, retriever_presets.HYBRID_PRESET_KEY)
    stored = _with_top_k(preset["params"], 2)
    snapshot = copy.deepcopy(stored)

    retriever_presets.match_preset_key(preset["component"], stored, _registry(client))

    assert stored == snapshot


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


def test_effective_chunk_count_caps_an_agentic_composite():
    """``max_chunks`` caps the pool, and the parent's window multiplies it."""
    children = [{"component": "BM25Retriever", "params": {"top_k": 20}}]
    capped = {"max_chunks": 5, "children": children}
    expanded = {**capped, ENABLE_FIELD: True, WINDOW_FIELD: 3}

    assert (
        retriever_presets.effective_chunk_count("AgenticSingleRetriever", capped) == 5
    )
    assert (
        retriever_presets.effective_chunk_count("AgenticSingleRetriever", expanded)
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


# ── Persistence signature ────────────────────────────────────────────────────


def test_changing_the_distance_metric_keeps_the_sparse_storage_folder(orm_db):
    """The distance metric acts at query time, so it never moves the folder."""
    service = _setup_service(orm_db, chunks=_artifact_corpus())
    params = bm25_retriever_params()
    other_metric = {
        **params,
        "similarity_function": {"component": "CosineSimilarity", "params": {"x": 1}},
    }

    assert (
        service._build_sparse_persistence_for(BM25Retriever, params).model_dir
        == service._build_sparse_persistence_for(BM25Retriever, other_metric).model_dir
    )


def test_signature_drops_query_time_params_and_keeps_nested_fitted_ones():
    """``top_k`` and the metric go; the vectorizer's parameters stay."""
    params = bm25_retriever_params()
    changed_vectorizer = {
        **params,
        "vectorizer": {"component": "BagOfWordsConverter", "params": {"lowercase": 0}},
    }

    base = persistence_signature(BM25Retriever, params, _REGISTRY)

    assert "top_k" not in base
    assert "similarity_function" not in base
    assert base == persistence_signature(
        BM25Retriever, {**params, "top_k": 9, **ENABLED_PARAMS}, _REGISTRY
    )
    assert base != persistence_signature(BM25Retriever, changed_vectorizer, _REGISTRY)


def test_signature_uses_the_declaration_of_nested_components():
    """A nested class's own ``NON_PERSISTENT_PARAMS`` applies inside the ref."""

    class Inner:
        NON_PERSISTENT_PARAMS = ("cache_size",)

    registry = {"Inner": {"class": Inner}}
    reference = {"component": "Inner", "params": {"cache_size": 1, "model": "m"}}

    class Outer:
        NON_PERSISTENT_PARAMS = ("top_k",)

    signature = persistence_signature(
        Outer, {"top_k": 3, "child": reference, "items": [reference]}, registry
    )

    expected = {"component": "Inner", "params": {"model": "m"}}
    assert signature == {"child": expected, "items": [expected]}


def test_signature_rejects_an_unregistered_nested_component():
    """A component the registry does not know is an error, not a default."""
    reference = {"component": "Missing", "params": {}}

    with pytest.raises(RAGComponentNotFoundError):
        persistence_signature(BM25Retriever, {"child": reference}, {})


def test_changing_the_distance_metric_does_not_delete_a_unit_retriever(
    client: TestClient, tmp_path
):
    """Only the metric and ``top_k`` changed, so the fitted retriever stays."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_metric_{uuid.uuid4().hex[:6]}"
        ).id
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
                "params": {
                    **params,
                    "top_k": 9,
                    "similarity_function": {
                        "component": "EuclideanSimilarity",
                        "params": {},
                    },
                },
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is not None
        assert db.get(RAGSparseRetriever, detail.id) is not None
        assert folder.exists()


# ── Embedding batch size ─────────────────────────────────────────────────────

_EMBEDDING_PARAMS: Dict[str, Any] = {
    "device": "cpu",
    "batch_size": 32,
    "normalize": True,
    "overflow_strategy": "truncate",
}
_EMBEDDING_REGISTRY = {"AllMiniLML6V2Embedding": {"class": AllMiniLML6V2Embedding}}
#: A device other than the CPU label, used to show the device never keys a row.
_GPU_DEVICE = "cuda:0"


def _dense_params(embedding_params: Dict[str, Any]) -> Dict[str, Any]:
    """Return dense retriever parameters around an embedding model's params."""
    return {
        "embedding_model": {
            "component": "AllMiniLML6V2Embedding",
            "params": embedding_params,
        },
        "similarity_metric": {"component": "CosineSimilarity", "params": {}},
        "top_k": 5,
    }


def _with_batch_size(params: Dict[str, Any], batch_size: int) -> Dict[str, Any]:
    """Return a configuration whose embedding model uses *batch_size*."""
    embedding = params["embedding_model"]
    return {
        **params,
        "embedding_model": {
            **embedding,
            "params": {**embedding["params"], "batch_size": batch_size},
        },
    }


@pytest.mark.parametrize(
    "embedding_class",
    [AllMiniLML6V2Embedding, DistilBERTEmbedding, E5MistralGGUFEmbedding],
)
def test_batch_size_is_left_out_of_every_embedding_signature(embedding_class):
    """Sentence-transformer, transformer and GGUF converters all inherit the rule."""
    small = persistence_signature(embedding_class, {"batch_size": 8}, {})
    large = persistence_signature(embedding_class, {"batch_size": 64}, {})

    assert small == large == {}


def test_batch_size_does_not_change_the_dense_signature():
    """A memory-only knob inside the embedding ref keeps the identity."""
    small = _dense_params({**_EMBEDDING_PARAMS, "batch_size": 8})
    large = _dense_params({**_EMBEDDING_PARAMS, "batch_size": 64})

    signature = persistence_signature(
        DenseEmbeddingRetriever, large, _EMBEDDING_REGISTRY
    )

    assert "batch_size" not in signature["embedding_model"]["params"]
    assert signature == persistence_signature(
        DenseEmbeddingRetriever, small, _EMBEDDING_REGISTRY
    )


def test_normalization_still_changes_the_dense_signature():
    """The control: an embedding parameter that shapes the vectors still counts."""
    base = _dense_params(_EMBEDDING_PARAMS)
    unnormalized = _dense_params({**_EMBEDDING_PARAMS, "normalize": False})

    assert persistence_signature(
        DenseEmbeddingRetriever, base, _EMBEDDING_REGISTRY
    ) != persistence_signature(
        DenseEmbeddingRetriever, unnormalized, _EMBEDDING_REGISTRY
    )


def test_batch_size_resolves_to_the_same_embedding_model_row(orm_db):
    """Only a vector-shaping change resolves to a new embedding model id.

    A batch size change keeps the stored embedding row, so the documents are not
    embedded again; normalization shapes the vectors and gets its own row.
    """
    service = RetrieverSetupService(
        db=orm_db,
        registry=_EMBEDDING_REGISTRY,
        env_RAG_path="rag-root",
        chunks={},
        chunk_set_id=7,
        pipeline_id=1,
        chunking_key="test-chunking",
    )
    small = service._build_dense_persistence_for(
        _dense_params({**_EMBEDDING_PARAMS, "batch_size": 8})
    )
    large = service._build_dense_persistence_for(
        _dense_params({**_EMBEDDING_PARAMS, "batch_size": 64})
    )
    unnormalized = service._build_dense_persistence_for(
        _dense_params({**_EMBEDDING_PARAMS, "normalize": False})
    )

    assert small.embedding_model_id == large.embedding_model_id
    assert unnormalized.embedding_model_id != small.embedding_model_id


def _dense_retriever_state(db, session_id: int, params: Dict[str, Any]):
    """Insert a session pipeline with one fitted dense retriever.

    The embedding row carries a unique marker instead of the converter params,
    because the table is unique on (class, parameters) and is shared by every
    test in the database. Cleanup never reads that row's parameters.
    """
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.flush()
    pipeline = RAGPipeline(session_id=session_id, name="")
    db.add(pipeline)
    db.flush()
    embedding_model = RAGEmbeddingModel(
        class_name="AllMiniLML6V2Embedding",
        parameters={"marker": uuid.uuid4().hex},
    )
    db.add(embedding_model)
    db.flush()
    bridge = RAGRetriever(class_name="DenseEmbeddingRetriever", pipeline_id=pipeline.id)
    db.add(bridge)
    db.flush()
    detail = RAGDenseRetriever(
        bridge_id=bridge.id,
        chunk_set_id=chunk_set.id,
        class_name="DenseEmbeddingRetriever",
        parameters=params,
        embedding_model_id=embedding_model.id,
    )
    db.add(detail)
    db.commit()
    return bridge, detail


def test_changing_the_batch_size_does_not_delete_a_dense_retriever(
    client: TestClient,
):
    """A batch size change keeps the fitted dense retriever and its embeddings."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_batch_{uuid.uuid4().hex[:6]}"
        ).id
        params = _dense_params(_EMBEDDING_PARAMS)
        bridge, detail = _dense_retriever_state(db, session_id, params)
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": params,
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": _with_batch_size(params, 8),
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is not None
        assert db.get(RAGDenseRetriever, detail.id) is not None


def test_changing_the_normalization_does_delete_a_dense_retriever(client: TestClient):
    """The control: a change to a vector-shaping parameter still triggers cleanup."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_norm_ctl_{uuid.uuid4().hex[:6]}"
        ).id
        params = _dense_params(_EMBEDDING_PARAMS)
        bridge, _ = _dense_retriever_state(db, session_id, params)
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": params,
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": _dense_params({**_EMBEDDING_PARAMS, "normalize": False}),
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is None


# ── Embedding device ─────────────────────────────────────────────────────────


def _with_device(params: Dict[str, Any], device: str) -> Dict[str, Any]:
    """Return a configuration whose embedding model runs on *device*."""
    embedding = params["embedding_model"]
    return {
        **params,
        "embedding_model": {
            **embedding,
            "params": {**embedding["params"], DEVICE_FIELD: device},
        },
    }


def _embedding_service(db) -> RetrieverSetupService:
    """Return a setup service whose registry knows the MiniLM embedding class."""
    return RetrieverSetupService(
        db=db,
        registry=_EMBEDDING_REGISTRY,
        env_RAG_path="rag-root",
        chunks={},
        chunk_set_id=7,
        pipeline_id=1,
        chunking_key="test-chunking",
    )


@pytest.mark.parametrize(
    "embedding_class",
    [AllMiniLML6V2Embedding, DistilBERTEmbedding, E5MistralGGUFEmbedding],
)
def test_device_is_left_out_of_every_embedding_signature(embedding_class):
    """The device only picks hardware, so every embedding converter ignores it."""
    cpu = persistence_signature(embedding_class, {DEVICE_FIELD: "cpu"}, {})
    gpu = persistence_signature(embedding_class, {DEVICE_FIELD: _GPU_DEVICE}, {})

    assert cpu == gpu == {}


def test_device_does_not_change_the_dense_signature():
    """A device change keeps the dense identity; the normalization control differs."""
    cpu = _dense_params(_EMBEDDING_PARAMS)
    gpu = _dense_params({**_EMBEDDING_PARAMS, DEVICE_FIELD: _GPU_DEVICE})
    unnormalized = _dense_params({**_EMBEDDING_PARAMS, "normalize": False})

    signature = persistence_signature(DenseEmbeddingRetriever, gpu, _EMBEDDING_REGISTRY)

    assert DEVICE_FIELD not in signature["embedding_model"]["params"]
    assert signature == persistence_signature(
        DenseEmbeddingRetriever, cpu, _EMBEDDING_REGISTRY
    )
    assert signature != persistence_signature(
        DenseEmbeddingRetriever, unnormalized, _EMBEDDING_REGISTRY
    )


def test_device_resolves_to_the_same_embedding_model_row(orm_db):
    """A device change keeps the stored row, so documents are not embedded again."""
    service = _embedding_service(orm_db)
    cpu = service._build_dense_persistence_for(_dense_params(_EMBEDDING_PARAMS))
    gpu = service._build_dense_persistence_for(
        _dense_params({**_EMBEDDING_PARAMS, DEVICE_FIELD: _GPU_DEVICE})
    )
    unnormalized = service._build_dense_persistence_for(
        _dense_params({**_EMBEDDING_PARAMS, "normalize": False})
    )

    assert gpu.embedding_model_id == cpu.embedding_model_id
    assert unnormalized.embedding_model_id != cpu.embedding_model_id


def test_persisted_embedding_row_leaves_out_the_query_time_params(orm_db):
    """The stored row keeps the vector-shaping options and drops batch and device."""
    service = _embedding_service(orm_db)
    persistence = service._build_dense_persistence_for(
        _dense_params(
            {**_EMBEDDING_PARAMS, BATCH_SIZE_FIELD: 8, DEVICE_FIELD: _GPU_DEVICE}
        )
    )
    row = orm_db.get(RAGEmbeddingModel, persistence.embedding_model_id)
    vector_params = {
        name: value
        for name, value in _EMBEDDING_PARAMS.items()
        if name not in (BATCH_SIZE_FIELD, DEVICE_FIELD)
    }

    assert BATCH_SIZE_FIELD not in row.parameters
    assert DEVICE_FIELD not in row.parameters
    assert row.parameters == vector_params


def test_legacy_embedding_row_with_query_time_params_is_not_reused(orm_db):
    """A row stored with batch size and device misses the cache and stays in place."""
    legacy = RAGEmbeddingModel(
        class_name="AllMiniLML6V2Embedding", parameters=dict(_EMBEDDING_PARAMS)
    )
    orm_db.add(legacy)
    orm_db.commit()
    service = _embedding_service(orm_db)

    first = service._build_dense_persistence_for(_dense_params(_EMBEDDING_PARAMS))
    second = service._build_dense_persistence_for(_dense_params(_EMBEDDING_PARAMS))

    created = orm_db.get(RAGEmbeddingModel, first.embedding_model_id)
    assert first.embedding_model_id != legacy.id
    assert BATCH_SIZE_FIELD not in created.parameters
    assert DEVICE_FIELD not in created.parameters
    assert orm_db.get(RAGEmbeddingModel, legacy.id) is not None
    assert second.embedding_model_id == first.embedding_model_id


def test_changing_the_device_does_not_delete_a_dense_retriever(client: TestClient):
    """A device change keeps the fitted dense retriever and its embeddings."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_device_{uuid.uuid4().hex[:6]}"
        ).id
        params = _dense_params(_EMBEDDING_PARAMS)
        bridge, detail = _dense_retriever_state(db, session_id, params)
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": params,
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": _with_device(params, _GPU_DEVICE),
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge.id) is not None
        assert db.get(RAGDenseRetriever, detail.id) is not None


# ── Composite and nested signatures ──────────────────────────────────────────

_COMPOSITE_REGISTRY = {
    **_REGISTRY,
    "MMRRerankerRetriever": {"class": MMRRerankerRetriever},
    "ParallelRetriever": {"class": ParallelRetriever},
}


def _mmr_params(top_k: int, mmr_lambda: float) -> Dict[str, Any]:
    """Return MMR reranker parameters over one BM25 child."""
    return {
        "children": [{"component": "BM25Retriever", "params": bm25_retriever_params()}],
        "mmr_lambda": mmr_lambda,
        "top_k": top_k,
    }


def test_mmr_top_k_and_lambda_do_not_change_the_signature():
    """MMR's selection knobs act at query time; only its child is persisted."""
    base = persistence_signature(
        MMRRerankerRetriever, _mmr_params(3, 0.5), _COMPOSITE_REGISTRY
    )
    retuned = persistence_signature(
        MMRRerankerRetriever, _mmr_params(7, 0.9), _COMPOSITE_REGISTRY
    )

    assert base == retuned
    assert list(base) == ["children"]


def test_parallel_merge_strategy_does_not_change_the_signature():
    """The merge strategy only combines child results at query time."""
    children = [{"component": "BM25Retriever", "params": bm25_retriever_params()}]
    round_robin = persistence_signature(
        ParallelRetriever,
        {"merge_strategy": "round_robin", "children": children},
        _COMPOSITE_REGISTRY,
    )
    interleave = persistence_signature(
        ParallelRetriever,
        {"merge_strategy": "interleave", "children": children},
        _COMPOSITE_REGISTRY,
    )

    assert round_robin == interleave


def test_nested_key_order_does_not_change_the_serialised_signature():
    """Natural-key lookups compare JSON text, so nested key order is canonical."""
    params = bm25_retriever_params()
    forward_vectorizer = {
        "component": "BagOfWordsConverter",
        "params": {"alpha": 1, "beta": 2},
    }
    backward_vectorizer = {
        "component": "BagOfWordsConverter",
        "params": {"beta": 2, "alpha": 1},
    }
    forward = persistence_signature(
        BM25Retriever, {**params, "vectorizer": forward_vectorizer}, _REGISTRY
    )
    backward = persistence_signature(
        BM25Retriever, {**params, "vectorizer": backward_vectorizer}, _REGISTRY
    )

    assert json.dumps(forward) == json.dumps(backward)


class _Holder:
    """A nested component class without a ``NON_PERSISTENT_PARAMS`` declaration."""


class _Inner:
    """A nested component class that declares one query-time parameter."""

    NON_PERSISTENT_PARAMS = ("cache_size",)


def test_refs_inside_a_plain_dict_value_are_resolved():
    """Plain dicts are searched for refs; undeclared classes keep all params."""
    registry = {"_Holder": {"class": _Holder}, "_Inner": {"class": _Inner}}
    params = {
        "kept": 1,
        "settings": {
            "child": {"component": "_Inner", "params": {"cache_size": 4, "model": "m"}}
        },
    }

    signature = persistence_signature(_Holder, params, registry)

    assert signature == {
        "kept": 1,
        "settings": {"child": {"component": "_Inner", "params": {"model": "m"}}},
    }


def test_a_component_ref_with_non_dict_params_names_the_component():
    """Malformed nested params raise a clear error instead of an AttributeError."""
    reference = {"component": "BagOfWordsConverter", "params": "lowercase"}

    with pytest.raises(ValueError, match="BagOfWordsConverter"):
        persistence_signature(BM25Retriever, {"vectorizer": reference}, _REGISTRY)


# ── Cleanup needs the registry only when it must compare ─────────────────────


def test_cleanup_without_a_registry_works_when_the_retriever_is_unchanged(orm_db):
    """An unchanged retriever is compared raw, so no registry is needed."""
    parameters = {
        "documents": [],
        "retriever_model": {
            "component": "BM25Retriever",
            "params": bm25_retriever_params(),
        },
    }

    CleanupService(orm_db).cleanup_orphaned_resources(
        999, parameters, copy.deepcopy(parameters)
    )


def test_unchanged_retriever_with_a_missing_plugin_does_not_raise(orm_db):
    """A retriever whose plugin is gone is left alone while it is unchanged."""
    parameters = {
        "documents": [],
        "retriever_model": {"component": "PluginOnlyRetriever", "params": {"x": 1}},
    }

    CleanupService(orm_db).cleanup_orphaned_resources(
        999, parameters, copy.deepcopy(parameters)
    )
    CleanupService(orm_db, {}).cleanup_orphaned_resources(
        999, parameters, copy.deepcopy(parameters)
    )


def test_changed_retriever_without_a_registry_raises_a_clear_error(orm_db):
    """A real change must be compared, which needs a registry."""
    old_parameters = {
        "documents": [],
        "retriever_model": {
            "component": "BM25Retriever",
            "params": bm25_retriever_params(),
        },
    }
    new_parameters = copy.deepcopy(old_parameters)
    new_parameters["retriever_model"]["params"]["k1"] = 2.0

    with pytest.raises(ValueError, match="registry"):
        CleanupService(orm_db).cleanup_orphaned_resources(
            999, old_parameters, new_parameters
        )


def test_changed_retriever_whose_old_plugin_is_gone_is_treated_as_changed(
    orm_db, caplog
):
    """An uninstalled plugin cannot be compared, so the switch must still go through.

    The old reference cannot be reduced to a signature, so it is taken as a real
    change: the session is updated and the user can move to another retriever.
    """
    old_parameters = {
        "documents": [],
        "retriever_model": {"component": "PluginOnlyRetriever", "params": {"x": 1}},
    }
    new_parameters = {
        "documents": [],
        "retriever_model": {
            "component": "BM25Retriever",
            "params": bm25_retriever_params(),
        },
    }

    with caplog.at_level(logging.WARNING, logger=CleanupService.__module__):
        CleanupService(orm_db, _REGISTRY).cleanup_orphaned_resources(
            999, old_parameters, new_parameters
        )

    assert "PluginOnlyRetriever" in caplog.text


_COMPOSITE_KNOB_CASES = [
    (
        "MMRRerankerRetriever",
        {"top_k": 3, "mmr_lambda": 0.5},
        {"top_k": 9, "mmr_lambda": 0.5},
    ),
    (
        "MMRRerankerRetriever",
        {"top_k": 3, "mmr_lambda": 0.5},
        {"top_k": 3, "mmr_lambda": 0.1},
    ),
    (
        "ParallelRetriever",
        {"merge_strategy": "round_robin"},
        {"merge_strategy": "interleave"},
    ),
]


@pytest.mark.parametrize(
    ("parent_class", "old_knobs", "new_knobs"), _COMPOSITE_KNOB_CASES
)
def test_changing_a_composite_knob_keeps_its_child_state(
    client: TestClient, tmp_path, parent_class, old_knobs, new_knobs
):
    """Composite knobs are query-time: the child's sparse row and folder stay."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(db, f"identity_knob_{uuid.uuid4().hex[:6]}").id
        child_params = bm25_retriever_params()
        parent, child_bridge, folder = _composite_retriever_state(
            db, session_id, tmp_path, child_params, parent_class=parent_class
        )
        children = [{"component": "BM25Retriever", "params": child_params}]
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": parent_class,
                "params": {**old_knobs, "children": children},
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": parent_class,
                "params": {**new_knobs, "children": children},
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, parent.id) is not None
        assert db.get(RAGRetriever, child_bridge.id) is not None
        assert (
            db.query(RAGSparseRetriever).filter_by(bridge_id=child_bridge.id).count()
            == 1
        )
        assert folder.exists()


# ── Index status readiness ───────────────────────────────────────────────────


def test_a_composite_with_a_non_dict_child_is_not_ready(orm_db):
    """A junk child cannot be verified, so the composite is not ready."""
    retriever = {
        "component": "ParallelRetriever",
        "params": {"merge_strategy": "round_robin", "children": ["junk"]},
    }
    service = IndexStatusService(orm_db, _COMPOSITE_REGISTRY)

    assert service._retriever_ready(retriever, 7) is False


def test_a_composite_without_children_is_not_ready(orm_db):
    """A composite with no ``children`` key has nothing to verify, so not ready."""
    retriever = {
        "component": "ParallelRetriever",
        "params": {"merge_strategy": "round_robin"},
    }
    service = IndexStatusService(orm_db, _COMPOSITE_REGISTRY)

    assert service._retriever_ready(retriever, 7) is False


def test_an_unregistered_nested_component_is_not_ready(orm_db):
    """An unknown nested component reports not-ready instead of raising."""
    params = {
        **bm25_retriever_params(),
        "vectorizer": {"component": "MissingConverter", "params": {}},
    }
    service = IndexStatusService(orm_db, _REGISTRY)

    assert (
        service._retriever_ready({"component": "BM25Retriever", "params": params}, 7)
        is False
    )


def test_a_wrapped_stored_retriever_is_matched_like_setup_matches_it(orm_db, tmp_path):
    """A ``properties``-wrapped stored retriever resolves to its fitted row."""
    session_id = _insert_rag_session(orm_db, f"identity_wrap_{uuid.uuid4().hex[:6]}").id
    params = bm25_retriever_params()
    signature = persistence_signature(BM25Retriever, params, _REGISTRY)
    _, detail, _ = _sparse_retriever_state(orm_db, session_id, tmp_path, signature)
    wrapped = {
        "properties": {
            "component": "BM25Retriever",
            "params": {"comp": {"component": "BM25Retriever", "params": params}},
        },
    }
    service = IndexStatusService(orm_db, _REGISTRY)

    assert service._retriever_ready(wrapped, detail.chunk_set_id) is True


# ── Bridge rows ──────────────────────────────────────────────────────────────


def test_unit_cleanup_removes_every_bridge_of_the_class(client: TestClient, tmp_path):
    """A stray bridge of the same class in the pipeline is removed too."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_stray_{uuid.uuid4().hex[:6]}"
        ).id
        params = bm25_retriever_params()
        bridge, detail, _ = _sparse_retriever_state(db, session_id, tmp_path, params)
        stray_bridge = RAGRetriever(
            class_name="BM25Retriever", pipeline_id=bridge.pipeline_id
        )
        db.add(stray_bridge)
        db.flush()
        db.add(
            RAGSparseRetriever(
                bridge_id=stray_bridge.id,
                chunk_set_id=detail.chunk_set_id,
                class_name="BM25Retriever",
                parameters={"k1": 9.0},
                storage_folder=str(tmp_path / "stray_folder"),
            )
        )
        db.commit()
        bridge_id = bridge.id
        stray_id = stray_bridge.id
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

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, bridge_id) is None
        assert db.get(RAGRetriever, stray_id) is None


def test_composite_cleanup_removes_its_child_bridges(client: TestClient, tmp_path):
    """A composite change deletes its child bridges and their links too."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session_id = _insert_rag_session(
            db, f"identity_childbr_{uuid.uuid4().hex[:6]}"
        ).id
        child_params = bm25_retriever_params()
        parent, child_bridge, _ = _composite_retriever_state(
            db, session_id, tmp_path, child_params
        )
        parent_id = parent.id
        child_bridge_id = child_bridge.id
        children = [{"component": "BM25Retriever", "params": child_params}]
        old_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "ParallelRetriever",
                "params": {"merge_strategy": "round_robin", "children": children},
            },
        }
        new_parameters = {
            "documents": [],
            "retriever_model": {
                "component": "ParallelRetriever",
                "params": {
                    "merge_strategy": "round_robin",
                    "children": [
                        {
                            "component": "BM25Retriever",
                            "params": {**child_params, "k1": 2.0},
                        }
                    ],
                },
            },
        }

        CleanupService(db, _registry(client)).cleanup_orphaned_resources(
            session_id, old_parameters, new_parameters
        )

        assert db.get(RAGRetriever, parent_id) is None
        assert db.get(RAGRetriever, child_bridge_id) is None
        assert (
            db.query(RAGRetrieverChild).filter_by(child_id=child_bridge_id).count() == 0
        )
