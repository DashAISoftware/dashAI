"""State persistence of the sparse retrievers.

A sparse retriever persists the fitted converter, its matrices and a
``row -> chunk id`` map. No chunk text is persisted: every row is resolved
through the chunks the current session injected, keyed by ``Chunk.id``.

``Chunk.id`` is the ordinal of the chunk in its chunk set (documents by
ascending id, then chunks by ascending position), so it is a property of the
corpus, not of the rows a session happened to store. Two sessions over the same
corpus therefore get the same ids and can share one fitted folder, while a
different corpus resolves to a different folder and is fitted from scratch —
the folder identity itself is pinned by ``test_retriever_identity.py``.
"""

import pickle
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pytest

from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter
from DashAI.back.converters.scikit_learn.tf_idf import TFIDFConverter
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever
from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import TFIDFRetriever
from tests.back.RAG.conftest import BOW_PARAMS, TFIDF_PARAMS

#: File each retriever persists its ``row -> chunk id`` map into.
ROW_MAP_FILE = {
    BM25Retriever: "bm25_row_to_chunk_id.pkl",
    TFIDFRetriever: "matrix_row_to_chunk_id.pkl",
}

#: Chunk ids deliberately offset from the row ordinals they are filed under.
OFFSET_CHUNK_ID = 500


def _chunk(chunk_id: int, document_id: int, text: str, position: int = 0) -> Chunk:
    """Build one chunk at the given document position.

    Parameters
    ----------
    chunk_id : int
        Value of ``Chunk.id``.
    document_id : int
        Parent document id.
    text : str
        Chunk text.
    position : int, optional
        Position of the chunk inside its document. Default 0.

    Returns
    -------
    Chunk
        The chunk.
    """
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        document_position=position,
        text=text,
    )


def _corpus(*chunks: Chunk) -> Dict[int, Dict[int, Chunk]]:
    """Group chunks into the nested corpus shape the retrievers expect.

    Parameters
    ----------
    *chunks : Chunk
        The chunks of the corpus.

    Returns
    -------
    Dict[int, Dict[int, Chunk]]
        ``{document_id: {position: chunk}}``.
    """
    corpus: Dict[int, Dict[int, Chunk]] = {}
    for chunk in chunks:
        corpus.setdefault(chunk.document_id, {})[chunk.document_position] = chunk
    return corpus


def _session_corpus(*texts: str) -> Dict[int, Dict[int, Chunk]]:
    """Build one chunk per document, numbered with session-scoped ordinals.

    Parameters
    ----------
    *texts : str
        Text of each document, in ascending document id order.

    Returns
    -------
    Dict[int, Dict[int, Chunk]]
        A corpus whose chunk ids are the ordinals ``0..len(texts)-1``.
    """
    return _corpus(
        *(
            _chunk(index, document_id=index + 1, text=text)
            for index, text in enumerate(texts)
        )
    )


def _bm25(corpus: Dict[int, Dict[int, Chunk]], model_dir: Path) -> BM25Retriever:
    """Build a BM25 retriever over *corpus*, restored from *model_dir*.

    Parameters
    ----------
    corpus : Dict[int, Dict[int, Chunk]]
        The chunks to index.
    model_dir : Path
        Direction holding the previously saved state, if any.

    Returns
    -------
    BM25Retriever
        The initialized retriever.
    """
    retriever = BM25Retriever(
        vectorizer=BagOfWordsConverter(**BOW_PARAMS),
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
    """Build a TF-IDF retriever over *corpus*, restored from *model_dir*.

    Parameters
    ----------
    corpus : Dict[int, Dict[int, Chunk]]
        The chunks to index.
    model_dir : Path
        Direction holding the previously saved state, if any.

    Returns
    -------
    TFIDFRetriever
        The initialized retriever.
    """
    retriever = TFIDFRetriever(
        vectorizer=TFIDFConverter(**TFIDF_PARAMS),
        similarity_function="cosine",
        top_k=5,
    )
    retriever.inject_infra(".", corpus, SparsePersistence(model_dir=str(model_dir)))
    retriever.init_model()
    return retriever


def _count_refits(monkeypatch, retriever_class: type) -> List[int]:
    """Instrument ``_fit`` and return the list it appends to on every refit.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch the class.
    retriever_class : type
        Retriever class whose ``_fit`` is counted.

    Returns
    -------
    List[int]
        Appended to once per ``_fit`` call.
    """
    refits: List[int] = []
    original = retriever_class._fit

    def counting_fit(self):
        refits.append(1)
        return original(self)

    monkeypatch.setattr(retriever_class, "_fit", counting_fit)
    return refits


BUILDERS: List[Tuple[Callable, type]] = [
    (_bm25, BM25Retriever),
    (_tfidf, TFIDFRetriever),
]
BUILDER_IDS = ["bm25", "tfidf"]


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_saved_state_maps_rows_to_chunk_ids(builder, retriever_class, tmp_path) -> None:
    """The persisted map holds chunk ids, never the chunk objects themselves."""
    corpus = _corpus(
        _chunk(OFFSET_CHUNK_ID, 1, "alpha beta"),
        _chunk(OFFSET_CHUNK_ID + 1, 2, "gamma delta"),
    )

    retriever = builder(corpus, tmp_path)
    retriever.save()

    with open(tmp_path / ROW_MAP_FILE[retriever_class], "rb") as f:
        stored = pickle.load(f)
    assert stored == {0: OFFSET_CHUNK_ID, 1: OFFSET_CHUNK_ID + 1}
    assert retriever.matrix_row_to_chunk_id == stored


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_a_reload_reuses_the_fitted_state(
    builder, retriever_class, monkeypatch, tmp_path
) -> None:
    """A saved folder is loaded instead of fitting the corpus again."""
    corpus = _session_corpus("alpha beta", "gamma delta")

    first = builder(corpus, tmp_path)
    first.save()

    refits = _count_refits(monkeypatch, retriever_class)
    reloaded = builder(corpus, tmp_path)

    assert refits == []
    assert reloaded.matrix_row_to_chunk_id == first.matrix_row_to_chunk_id


@pytest.mark.parametrize("builder", [_bm25, _tfidf], ids=BUILDER_IDS)
def test_a_reload_returns_the_current_sessions_chunk_objects(builder, tmp_path) -> None:
    """Rows resolve through the injected chunks, never through stored objects."""
    first = builder(_session_corpus("alpha beta", "gamma delta"), tmp_path)
    first.save()

    current = _session_corpus("alpha beta", "gamma delta")
    reloaded = builder(current, tmp_path)

    results, trace = reloaded.retrieve("gamma")

    assert results[0] is current[2][0]
    assert trace["chunks"] == ["2_0", "1_0"]


@pytest.mark.parametrize("builder", [_bm25, _tfidf], ids=BUILDER_IDS)
def test_rows_follow_document_position_not_insertion_order(builder, tmp_path) -> None:
    """The row map is ordered by position, whatever order the dict has."""
    corpus = {
        1: {
            1: _chunk(OFFSET_CHUNK_ID + 1, 1, "gamma delta", position=1),
            0: _chunk(OFFSET_CHUNK_ID, 1, "alpha beta", position=0),
        }
    }

    retriever = builder(corpus, tmp_path)

    assert retriever.matrix_row_to_chunk_id == {
        0: OFFSET_CHUNK_ID,
        1: OFFSET_CHUNK_ID + 1,
    }
    results, _ = retriever.retrieve("gamma")
    assert results[0] is corpus[1][1]


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_a_folder_without_state_is_fitted_from_scratch(
    builder, retriever_class, monkeypatch, tmp_path
) -> None:
    """A corpus that resolves to a state-less folder is fitted, not reused."""
    refits = _count_refits(monkeypatch, retriever_class)

    retriever = builder(_session_corpus("gamma delta"), tmp_path / "unsaved")

    assert refits == [1]
    results, _ = retriever.retrieve("gamma")
    assert results[0].text == "gamma delta"


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_a_reused_folder_is_not_rewritten(builder, retriever_class, tmp_path) -> None:
    """A loaded folder reports that it needs no save; a fitted one does.

    ``RetrieverSetupService._save_sparse`` persists only when ``needs_save()``
    is true, so this predicate is what keeps a shared folder from being rewritten
    on every session that reuses it.
    """
    corpus = _session_corpus("alpha beta", "gamma delta")
    first = builder(corpus, tmp_path)
    first.save()

    reloaded = builder(corpus, tmp_path)
    fitted = builder(_session_corpus("gamma delta"), tmp_path / "unsaved")

    assert reloaded.needs_save() is False
    assert fitted.needs_save() is True


@pytest.mark.parametrize(("builder", "retriever_class"), BUILDERS, ids=BUILDER_IDS)
def test_a_row_map_from_another_corpus_is_rejected(
    builder, retriever_class, monkeypatch, tmp_path
) -> None:
    """A folder whose row map does not fit the corpus is refitted, not trusted."""
    first = builder(_session_corpus("alpha beta", "gamma delta"), tmp_path)
    first.save()

    stale = {0: OFFSET_CHUNK_ID, 1: OFFSET_CHUNK_ID + 99}
    with open(tmp_path / ROW_MAP_FILE[retriever_class], "wb") as f:
        pickle.dump(stale, f)

    refits = _count_refits(monkeypatch, retriever_class)
    retriever = builder(_session_corpus("alpha beta", "gamma delta"), tmp_path)

    assert refits == [1]
    assert retriever.matrix_row_to_chunk_id == {0: 0, 1: 1}
    results, _ = retriever.retrieve("gamma")
    assert results[0].text == "gamma delta"
