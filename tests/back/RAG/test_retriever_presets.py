"""Tests for the retriever-presets endpoint."""

import copy

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.config_builder import get_initial_components
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.services.RAG.legacy_retrievers import translate_legacy_retriever
from DashAI.back.services.RAG.retriever_presets import match_preset_key

#: Retrievers exactly as v0.11.0 stored them for the keyword and hybrid
#: presets: no retrieve-then-expand options at any level, and the similarity
#: metrics as scikit-learn names.
_V0110_BM25 = {
    "component": "BM25Retriever",
    "params": {
        "vectorizer": {
            "component": "BagOfWordsConverter",
            "params": {
                "max_features": None,
                "lowercase": True,
                "strip_accents": None,
                "analyzer": "word",
                "stop_words": None,
                "custom_stop_words": None,
                "lower_bound_ngrams": 1,
                "upper_bound_ngrams": 1,
                "min_df": 0.0,
                "max_df": 1.0,
                "drop_source_columns": False,
            },
        },
        "k1": 1.5,
        "b": 0.75,
        "delta": 0.0,
        "similarity_function": "cosine",
        "top_k": 10,
    },
}
_V0110_DENSE = {
    "component": "DenseEmbeddingRetriever",
    "params": {
        "embedding_model": {
            "component": "ParaphraseMultilingualMiniLML12V2Embedding",
            "params": {
                "device": "CPU",
                "batch_size": 32,
                "normalize": True,
                "overflow_strategy": "truncate",
            },
        },
        "similarity_metric": "cosine",
        "top_k": 5,
    },
}
_V0110_HYBRID = {
    "component": "ParallelRetriever",
    "params": {
        "merge_strategy": "round_robin",
        "children": [_V0110_BM25, _V0110_DENSE],
    },
}


@pytest.fixture(scope="module", name="registry")
def fixture_registry():
    return ComponentRegistry(initial_components=get_initial_components())


def test_retriever_presets_returns_three_presets(client: TestClient):
    response = client.get("/api/v1/rag/retriever-presets", params={"top_k": 10})
    assert response.status_code == 200
    data = response.json()
    assert [p["key"] for p in data] == ["keyword", "semantic", "hybrid"]


def test_keyword_preset(client: TestClient):
    data = client.get("/api/v1/rag/retriever-presets", params={"top_k": 10}).json()
    keyword = data[0]
    assert keyword["component"] == "BM25Retriever"
    assert keyword["params"]["top_k"] == 10
    assert keyword["params"]["vectorizer"]["component"] == "BagOfWordsConverter"
    assert "k1" in keyword["params"]


def test_semantic_preset(client: TestClient):
    data = client.get("/api/v1/rag/retriever-presets", params={"top_k": 10}).json()
    semantic = data[1]
    assert semantic["component"] == "DenseEmbeddingRetriever"
    assert semantic["params"]["top_k"] == 10
    emb = semantic["params"]["embedding_model"]
    assert emb["component"] == "ParaphraseMultilingualMiniLML12V2Embedding"


def test_hybrid_preset_splits_top_k(client: TestClient):
    data = client.get("/api/v1/rag/retriever-presets", params={"top_k": 15}).json()
    hybrid = data[2]
    assert hybrid["component"] == "ParallelRetriever"
    assert hybrid["params"]["merge_strategy"] == "round_robin"
    children = hybrid["params"]["children"]
    assert children[0]["component"] == "BM25Retriever"
    assert children[0]["params"]["top_k"] == 8  # ceil(15/2)
    assert children[1]["component"] == "DenseEmbeddingRetriever"
    assert children[1]["params"]["top_k"] == 7  # floor(15/2)


def test_retriever_presets_rejects_invalid_top_k(client: TestClient):
    response = client.get("/api/v1/rag/retriever-presets", params={"top_k": 0})
    assert response.status_code == 422


def test_hybrid_preset_children_carry_their_schema_defaults(client: TestClient):
    """Each child is completed with its defaults, like the top level."""
    data = client.get("/api/v1/rag/retriever-presets", params={"top_k": 10}).json()
    for child in data[2]["params"]["children"]:
        assert child["params"]["enable_retrieve_then_expand"] is False
        assert "expand_window" in child["params"]


@pytest.mark.parametrize(
    ("stored", "preset_key"),
    [(_V0110_BM25, "keyword"), (_V0110_HYBRID, "hybrid")],
)
def test_a_retriever_converted_from_v0110_keeps_its_preset(
    registry, stored, preset_key
):
    """The startup backfill completes every level with its defaults.

    A hybrid preset completed only at the top level never matched the
    converted sessions, so every hybrid session showed as a custom
    configuration after upgrading from v0.11.0.
    """
    translated = translate_legacy_retriever(copy.deepcopy(stored), registry)

    assert (
        match_preset_key(translated["component"], translated["params"], registry)
        == preset_key
    )
