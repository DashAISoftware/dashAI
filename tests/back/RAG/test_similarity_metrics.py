"""Similarity metrics are configurable components the vector retrievers rank with.

Every metric is a distance: a lower value means a more relevant chunk, so the
retrievers sort ascending. The legacy string values (``"cosine"``, ``"l2"``...)
must keep their meaning when a stored configuration is translated.
"""

import copy

import numpy as np
import pytest
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import pairwise_distances
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.converters.hugging_face.text_embedding import (
    MultilingualE5SmallEmbedding,
)
from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter
from DashAI.back.converters.scikit_learn.tf_idf import TFIDFConverter
from DashAI.back.dependencies.config_builder import get_initial_components
from DashAI.back.dependencies.database.backfill import backfill_rag_retrievers
from DashAI.back.dependencies.database.models import Base, GenerativeSession
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence import DensePersistence
from DashAI.back.models.RAG.retrievers.similarity import (
    BaseSimilarityMetric,
    CosineSimilarity,
    EuclideanSimilarity,
    ManhattanSimilarity,
)
from DashAI.back.models.RAG.retrievers.sparse import BM25Retriever, TFIDFRetriever
from DashAI.back.services.RAG.legacy_retrievers import translate_legacy_retriever
from DashAI.back.services.RAG.session_validation_service import (
    SessionValidationService,
)
from tests.back.converters.text_embedding_stub import with_fake_model
from tests.back.RAG.conftest import rag_session_columns

LANGUAGES = ("en", "es", "pt", "de", "zh")

#: Vector size of the fake sentence model, so no download happens.
FAKE_DIM = 8
DOCUMENT_ID = 1

#: Registered metric component names, by class.
COSINE = "CosineSimilarity"
EUCLIDEAN = "EuclideanSimilarity"
MANHATTAN = "ManhattanSimilarity"

#: Every legacy string the stored configurations used, and the metric it became.
LEGACY_ALIASES = {
    "cosine": COSINE,
    "euclidean": EUCLIDEAN,
    "l2": EUCLIDEAN,
    "cityblock": MANHATTAN,
    "l1": MANHATTAN,
    "manhattan": MANHATTAN,
}

VECTORS = np.array(
    [
        [1.0, 0.0, 2.0],
        [0.0, 3.0, 1.0],
        [2.0, 2.0, 0.0],
    ]
)
QUERY = np.array([[1.0, 1.0, 0.0]])


@pytest.fixture(scope="module", name="registry")
def fixture_registry():
    return ComponentRegistry(initial_components=get_initial_components())


@pytest.fixture(name="factory")
def fixture_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'metrics.db'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


def _legacy_bm25(metric) -> dict:
    """Return a BM25 retriever as v0.10.0 stored it, with the given metric."""
    return {
        "component": "BM25Retriever",
        "params": {
            "BM25Vectorizer": {
                "component": "BM25VectorizerModel",
                "params": {
                    "strip_accents": None,
                    "lowercase": True,
                    "stop_words": None,
                    "max_df": 1.0,
                    "min_df": 0.0,
                    "max_features": None,
                },
            },
            "k1": 1.5,
            "b": 0.75,
            "delta": 0.0,
            "similarity_function": metric,
            "top_k": 4,
        },
    }


def _legacy_dense(metric) -> dict:
    """Return a dense retriever whose embedding model no converter serves.

    The metric alone is under test, so the embedding part is left unchanged.
    """
    return {
        "component": "DenseEmbeddingRetriever",
        "params": {
            "embedding_model": {
                "component": "BERTEmbedding",
                "params": {"model_name": "google-bert/bert-base-cased"},
            },
            "similarity_metric": metric,
            "top_k": 5,
        },
    }


def _session(factory, name, retriever) -> int:
    """Insert a RAG session with a stored retriever and return its id."""
    with factory() as db:
        session = GenerativeSession(
            name=name,
            **rag_session_columns(
                {"documents": [], "retriever_model": copy.deepcopy(retriever)}
            ),
        )
        db.add(session)
        db.commit()
        return session.id


# --------------------------------------------------------------------------- #
# The metrics compute distances
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("metric_class", "sklearn_name"),
    [
        (CosineSimilarity, "cosine"),
        (EuclideanSimilarity, "euclidean"),
        (ManhattanSimilarity, "manhattan"),
    ],
)
def test_dense_distances_match_sklearn(metric_class, sklearn_name):
    """Each metric is exactly the scikit-learn distance it names."""
    expected = pairwise_distances(QUERY, VECTORS, metric=sklearn_name)

    actual = metric_class().distances(QUERY, VECTORS)

    np.testing.assert_allclose(actual, expected)


@pytest.mark.parametrize(
    ("metric_class", "sklearn_name"),
    [
        (CosineSimilarity, "cosine"),
        (EuclideanSimilarity, "euclidean"),
        (ManhattanSimilarity, "manhattan"),
    ],
)
def test_sparse_distances_match_sklearn(metric_class, sklearn_name):
    """Sparse TF-IDF and BM25 matrices are scored the same way."""
    query, vectors = csr_matrix(QUERY), csr_matrix(VECTORS)
    expected = pairwise_distances(query, vectors, metric=sklearn_name)

    actual = metric_class().distances(query, vectors)

    np.testing.assert_allclose(actual, expected)


def test_a_vector_is_at_zero_cosine_distance_from_itself():
    """The closest vector to a query equal to itself is the vector itself."""
    distances = CosineSimilarity().distances(VECTORS[:1], VECTORS)

    assert distances[0, 0] == pytest.approx(0.0, abs=1e-12)
    assert int(np.argmin(distances[0])) == 0


@pytest.mark.parametrize("metric_class", [EuclideanSimilarity, ManhattanSimilarity])
def test_the_nearest_vector_ranks_first(metric_class):
    """Lower is more relevant: the query's own vector gets the lowest distance."""
    query = VECTORS[1:2]

    distances = metric_class().distances(query, VECTORS)

    assert distances[0, 1] == pytest.approx(0.0)
    assert int(np.argmin(distances[0])) == 1


# --------------------------------------------------------------------------- #
# The metrics are registered components
# --------------------------------------------------------------------------- #


def test_the_metrics_are_registered_under_their_type(registry):
    """Every metric class is a SimilarityMetric component."""
    registered = registry.registry["SimilarityMetric"]

    assert set(registered) == {COSINE, EUCLIDEAN, MANHATTAN}
    assert registered[COSINE]["class"] is CosineSimilarity
    assert registered[EUCLIDEAN]["class"] is EuclideanSimilarity
    assert registered[MANHATTAN]["class"] is ManhattanSimilarity


@pytest.mark.parametrize("name", [COSINE, EUCLIDEAN, MANHATTAN])
def test_each_metric_has_an_empty_schema_and_multilingual_names(registry, name):
    """A metric has no parameters, but its name is shown in every language."""
    entry = registry[name]

    assert entry["schema"].get("properties", {}) == {}
    for language in LANGUAGES:
        assert getattr(entry["display_name"], language)
        assert getattr(entry["description"], language)


def test_the_retriever_fields_offer_the_metric_children(registry):
    """The component field lists every concrete metric as a choice."""
    children = registry.get_child_components(
        BaseSimilarityMetric.__name__, recursive=True
    )

    assert {child["name"] for child in children} == {COSINE, EUCLIDEAN, MANHATTAN}


@pytest.mark.parametrize(
    ("retriever_class", "field"),
    [
        (DenseEmbeddingRetriever, "similarity_metric"),
        (TFIDFRetriever, "similarity_function"),
        (BM25Retriever, "similarity_function"),
    ],
)
def test_the_retriever_fields_are_component_references(retriever_class, field):
    """The field is a component of the metric family, defaulting to cosine."""
    prop = retriever_class.get_schema()["properties"][field]

    assert prop["parent"] == BaseSimilarityMetric.__name__
    assert prop["placeholder"] == {"component": COSINE, "params": {}}


# --------------------------------------------------------------------------- #
# Retrievers take a live metric instance
# --------------------------------------------------------------------------- #


def test_dense_retriever_rejects_a_metric_name():
    """A bare string is not a metric; the retriever needs the component."""
    with pytest.raises(TypeError):
        DenseEmbeddingRetriever(
            embedding_model=MultilingualE5SmallEmbedding(),
            similarity_metric="cosine",
            top_k=2,
        )


def test_tfidf_retriever_rejects_a_metric_name():
    with pytest.raises(TypeError):
        TFIDFRetriever(
            vectorizer=TFIDFConverter(),
            similarity_function="cosine",
            top_k=2,
        )


def test_bm25_retriever_rejects_a_metric_name():
    with pytest.raises(TypeError):
        BM25Retriever(
            vectorizer=BagOfWordsConverter(),
            k1=1.5,
            b=0.75,
            delta=0.0,
            similarity_function="cosine",
            top_k=2,
        )


def test_the_dense_retriever_scores_with_the_injected_metric(tmp_path):
    """Retrieval calls the metric instance the retriever was built with."""
    calls = []

    class RecordingMetric(BaseSimilarityMetric):
        SKLEARN_METRIC = "euclidean"

        def distances(self, queries, vectors):
            calls.append(vectors.shape)
            return super().distances(queries, vectors)

    embedding = MultilingualE5SmallEmbedding()
    with_fake_model(embedding, dim=FAKE_DIM)
    chunks = {
        DOCUMENT_ID: {
            index: Chunk(
                id=index,
                document_id=DOCUMENT_ID,
                document_position=index,
                text=f"passage number {index}",
            )
            for index in range(3)
        }
    }
    persistence = DensePersistence(
        matrix_dirs={DOCUMENT_ID: str(tmp_path / "matrix")}, embedding_model_id=1
    )
    retriever = DenseEmbeddingRetriever(
        embedding_model=embedding,
        similarity_metric=RecordingMetric(),
        top_k=2,
    )
    retriever.inject_infra(str(tmp_path), chunks, persistence)
    retriever.init_model()

    results, _ = retriever.retrieve("passage number 1")

    assert len(results) == 2
    assert calls == [(3, FAKE_DIM)]
    assert retriever.similarity_metric == "RecordingMetric"


# --------------------------------------------------------------------------- #
# Legacy values are translated
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("alias", "component"), list(LEGACY_ALIASES.items()))
def test_each_legacy_sparse_alias_becomes_its_metric(registry, alias, component):
    """BM25 and TF-IDF share the ``similarity_function`` key."""
    translated = translate_legacy_retriever(_legacy_bm25(alias), registry)

    assert translated["params"]["similarity_function"] == {
        "component": component,
        "params": {},
    }


@pytest.mark.parametrize(("alias", "component"), list(LEGACY_ALIASES.items()))
def test_each_legacy_dense_alias_becomes_its_metric(registry, alias, component):
    translated = translate_legacy_retriever(_legacy_dense(alias), registry)

    assert translated["params"]["similarity_metric"] == {
        "component": component,
        "params": {},
    }


def test_composite_children_have_their_metric_translated(registry):
    """A legacy metric inside a composite child is translated too."""
    hybrid = {
        "component": "ParallelRetriever",
        "params": {
            "merge_strategy": "round_robin",
            "children": [_legacy_bm25("l1"), _legacy_dense("manhattan")],
        },
    }

    children = translate_legacy_retriever(hybrid, registry)["params"]["children"]

    assert children[0]["params"]["similarity_function"]["component"] == MANHATTAN
    assert children[1]["params"]["similarity_metric"]["component"] == MANHATTAN


def test_a_current_metric_reference_is_left_alone(registry):
    ref = {"component": EUCLIDEAN, "params": {}}
    retriever = _legacy_bm25("cosine")
    retriever["params"]["similarity_function"] = copy.deepcopy(ref)

    translated = translate_legacy_retriever(retriever, registry)

    assert translated["params"]["similarity_function"] == ref


@pytest.mark.parametrize(
    "value",
    ["dot", "chebyshev", "", None, 3, ["cosine"]],
)
def test_a_malformed_legacy_metric_raises(registry, value):
    """An unknown value is an error, never a silent switch to the default."""
    with pytest.raises(ValueError, match="Unknown similarity metric"):
        translate_legacy_retriever(_legacy_bm25(value), registry)


def test_a_malformed_metric_reference_raises(registry):
    """A dict that is not a component reference is reported as malformed."""
    with pytest.raises(ValueError, match="Malformed similarity metric"):
        translate_legacy_retriever(_legacy_bm25({"metric": "cosine"}), registry)


def test_a_stored_retriever_without_a_metric_raises(registry):
    """A missing metric is stale data, not a reason to default to cosine."""
    legacy = _legacy_bm25("cosine")
    del legacy["params"]["similarity_function"]
    with pytest.raises(ValueError, match="has no 'similarity_function'"):
        translate_legacy_retriever(legacy, registry)


# --------------------------------------------------------------------------- #
# The startup backfill converts stored sessions
# --------------------------------------------------------------------------- #


def test_backfill_converts_a_stored_legacy_metric(factory, registry):
    legacy = _session(factory, "legacy", _legacy_bm25("l1"))

    backfill_rag_retrievers(factory, registry)

    with factory() as db:
        session = db.get(GenerativeSession, legacy)
        retriever = session.parameters["retriever_model"]
        assert retriever["params"]["similarity_function"] == {
            "component": MANHATTAN,
            "params": {},
        }
        assert session.needs_reindex is True
        SessionValidationService(db, registry).validate_stored_retriever(
            session.parameters
        )


def test_backfill_leaves_a_session_with_an_unknown_metric_untouched(factory, registry):
    stored = _legacy_bm25("dot")
    broken = _session(factory, "broken", stored)

    backfill_rag_retrievers(factory, registry)

    with factory() as db:
        session = db.get(GenerativeSession, broken)
        assert session.parameters["retriever_model"] == stored
        assert session.needs_reindex is False


def test_the_default_recipes_name_the_registered_cosine_metric(registry):
    """The recipes name the metric by string; that name must be the class name."""
    from DashAI.back.models.RAG import RAG_defaults

    expected = {"component": COSINE, "params": {}}
    assert RAG_defaults.COSINE_SIMILARITY_COMPONENT == COSINE
    assert registry[COSINE]["class"] is CosineSimilarity
    assert RAG_defaults.default_keyword_retriever()["params"][
        "similarity_function"
    ] == (expected)
    assert RAG_defaults.default_semantic_retriever()["params"]["similarity_metric"] == (
        expected
    )
