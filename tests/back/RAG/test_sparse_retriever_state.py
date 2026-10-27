"""Regression tests for sparse-retriever state, and its cross-session reuse.

Sparse state is content-addressed: two sessions over the same corpus share one
fitted folder. The persisted row→chunk map therefore holds *another* session's
``Chunk`` objects, whose database ids differ, so it must be rebound to the
current chunks before it is trusted — and rejected when the content changed.
"""

from pathlib import Path
from typing import Callable, Dict, List

import pytest

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import (
    BM25Retriever,
    BM25VectorizerModel,
)
from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import (
    TFIDFRetriever,
    TFIDFVectorizerModel,
)


def _chunk(chunk_id: int, document_id: int, text: str) -> Chunk:
    """Build a one-position chunk for the given document."""
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        document_position=0,
        text=text,
    )


def _corpus(*chunks: Chunk) -> Dict[int, Dict[int, Chunk]]:
    """Group chunks into the nested corpus shape the retrievers expect."""
    corpus: Dict[int, Dict[int, Chunk]] = {}
    for chunk in chunks:
        corpus.setdefault(chunk.document_id, {})[chunk.document_position] = chunk
    return corpus


def _bm25(corpus: Dict[int, Dict[int, Chunk]], model_dir: Path) -> BM25Retriever:
    """Build a BM25 retriever over *corpus* using *model_dir*."""
    retriever = BM25Retriever(
        BM25Vectorizer=BM25VectorizerModel(
            strip_accents=None,
            lowercase=True,
            stop_words=None,
            max_df=1.0,
            min_df=0.0,
            max_features=None,
        ),
        k1=1.5,
        b=0.75,
        delta=0.0,
        similarity_function="cosine",
        top_k=5,
    )
    retriever.inject_infra(".", corpus, SparsePersistence(model_dir=str(model_dir)))
    retriever.init_model()
    return retriever


def _tfidf(corpus: Dict[int, Dict[int, Chunk]], model_dir: Path) -> TFIDFRetriever:
    """Build a TF-IDF retriever over *corpus* using *model_dir*."""
    retriever = TFIDFRetriever(
        TFIDFVectorizer=TFIDFVectorizerModel(
            strip_accents="None",
            lowercase=True,
            analyzer="word",
            stop_words=[],
            ngram_range=[1, 1],
            max_df=1.0,
            min_df=0.0,
            max_features=1000,
            norm="l2",
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=False,
        ),
        similarity_function="cosine",
        top_k=5,
    )
    retriever.inject_infra(".", corpus, SparsePersistence(model_dir=str(model_dir)))
    retriever.init_model()
    return retriever


def _count_refits(monkeypatch, retriever_class: type) -> List[int]:
    """Instrument ``_fit`` and return the list it appends to on every refit."""
    refits: List[int] = []
    original = retriever_class._fit

    def counting_fit(self):
        refits.append(1)
        return original(self)

    monkeypatch.setattr(retriever_class, "_fit", counting_fit)
    return refits


BUILDERS: List[tuple[Callable, type]] = [
    (_bm25, BM25Retriever),
    (_tfidf, TFIDFRetriever),
]
BUILDER_IDS = ["bm25", "tfidf"]


@pytest.mark.parametrize("builder", [_bm25, _tfidf], ids=["bm25", "tfidf"])
def test_stale_state_is_rejected_and_refitted(builder, tmp_path):
    """A persisted map from another corpus is ignored, never returned."""
    old_corpus = _corpus(
        _chunk(1, 1, "alpha beta"),
        _chunk(2, 2, "gamma delta"),
    )
    new_corpus = _corpus(_chunk(3, 3, "epsilon zeta"))

    old = builder(old_corpus, tmp_path)
    old.save()

    retriever = builder(new_corpus, tmp_path)

    stored_documents = {
        chunk.document_id for chunk in retriever.matrix_row_to_chunk_map.values()
    }
    assert stored_documents == {3}

    results, _ = retriever.retrieve("epsilon")
    assert results
    assert all(chunk.document_id == 3 for chunk in results)


@pytest.mark.parametrize("builder", [_bm25, _tfidf], ids=["bm25", "tfidf"])
def test_matching_state_is_loaded_without_refitting(builder, tmp_path):
    """A map that matches the injected corpus is still a valid cache hit."""
    corpus = _corpus(_chunk(1, 1, "alpha beta"), _chunk(2, 2, "gamma delta"))

    first = builder(corpus, tmp_path)
    first.save()
    first_map = {
        (chunk.document_id, chunk.document_position, chunk.id, chunk.hash)
        for chunk in first.matrix_row_to_chunk_map.values()
    }

    loaded = builder(corpus, tmp_path)
    loaded_map = {
        (chunk.document_id, chunk.document_position, chunk.id, chunk.hash)
        for chunk in loaded.matrix_row_to_chunk_map.values()
    }

    assert loaded_map == first_map
    results, _ = loaded.retrieve("alpha")
    assert results
    assert {chunk.document_id for chunk in results} <= {1, 2}


def test_chunk_map_match_requires_the_same_chunk_hashes(tmp_path):
    """Reused chunk ids with different text are not treated as a cache hit."""
    old_corpus = _corpus(_chunk(1, 1, "alpha beta"))
    new_corpus = _corpus(_chunk(1, 2, "gamma delta"))

    old = _bm25(old_corpus, tmp_path)
    old.save()

    retriever = _bm25(new_corpus, tmp_path)

    assert all(
        chunk.document_id == 2 for chunk in retriever.matrix_row_to_chunk_map.values()
    )


# ── Cross-session reuse ──────────────────────────────────────────────────────


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_another_session_loads_the_state_with_its_own_chunk_ids(
    builder, retriever_class, monkeypatch, tmp_path
):
    """Session B loads A's fitted state and returns B's chunk ids."""
    session_a = _corpus(_chunk(1, 1, "alpha beta"), _chunk(2, 2, "gamma delta"))
    session_b = _corpus(_chunk(501, 1, "alpha beta"), _chunk(502, 2, "gamma delta"))

    first = builder(session_a, tmp_path)
    first.save()

    refits = _count_refits(monkeypatch, retriever_class)
    loaded = builder(session_b, tmp_path)

    assert refits == []
    rebound = loaded.matrix_row_to_chunk_map
    assert set(rebound) == set(first.matrix_row_to_chunk_map)
    assert {chunk.id for chunk in rebound.values()} == {501, 502}

    results, _ = loaded.retrieve("alpha")
    assert results
    assert results[0].id == 501
    assert {chunk.id for chunk in results} == {501, 502}


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_different_content_refits_instead_of_rebinding(
    builder, retriever_class, monkeypatch, tmp_path
):
    """Same positions and ids, different text: the stored state is refitted."""
    session_a = _corpus(_chunk(1, 1, "alpha beta"))
    session_b = _corpus(_chunk(1, 1, "gamma delta"))

    first = builder(session_a, tmp_path)
    first.save()

    refits = _count_refits(monkeypatch, retriever_class)
    rebuilt = builder(session_b, tmp_path)

    assert refits == [1]
    assert {chunk.text for chunk in rebuilt.matrix_row_to_chunk_map.values()} == {
        "gamma delta"
    }
