"""Sparse retrievers fit and reload the converter they are given.

``retrieve`` returns ``(chunks, trace)`` for every retriever, so these tests
unpack the tuple and check the trace node names the retriever that produced the
chunks.
"""

import pickle

from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter
from DashAI.back.converters.scikit_learn.tf_idf import TFIDFConverter
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever
from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import TFIDFRetriever
from tests.back.RAG.conftest import BOW_PARAMS, TFIDF_PARAMS

TEXTS = [
    "cats purr when they are happy",
    "dogs bark at the mail carrier",
    "the stock market fell sharply today",
]

#: Position of the chunk every test query below matches.
STOCK_MARKET_POSITION = 2
CATS_POSITION = 0


def _chunks(with_empty_document=False):
    """Build ``{document_id: {position: Chunk}}`` for the sample texts."""
    chunks = {
        1: {
            index: Chunk(id=index, document_id=1, document_position=index, text=text)
            for index, text in enumerate(TEXTS)
        }
    }
    if with_empty_document:
        chunks[2] = {}
    return chunks


def _bm25(tmp_path):
    """Build a BM25 retriever over the sample corpus, restored from disk."""
    retriever = BM25Retriever(
        vectorizer=BagOfWordsConverter(**BOW_PARAMS),
        k1=1.5,
        b=0.75,
        delta=0.0,
        similarity_function="cosine",
        top_k=1,
    )
    retriever.inject_infra(
        str(tmp_path), _chunks(), SparsePersistence(model_dir=str(tmp_path / "bm25"))
    )
    return retriever


def _tfidf(tmp_path):
    """Build a TF-IDF retriever over the sample corpus, restored from disk."""
    retriever = TFIDFRetriever(
        vectorizer=TFIDFConverter(**TFIDF_PARAMS),
        similarity_function="cosine",
        top_k=1,
    )
    retriever.inject_infra(
        str(tmp_path), _chunks(), SparsePersistence(model_dir=str(tmp_path / "tfidf"))
    )
    return retriever


def _top_chunk(retriever, query):
    """Return the first ranked chunk of *query*, checking the tuple contract.

    Parameters
    ----------
    retriever : SparseRetriever
        A fitted sparse retriever.
    query : str
        The search query.

    Returns
    -------
    Chunk
        The best ranked chunk, with the trace node already validated.
    """
    chunks, trace = retriever.retrieve(query)
    assert isinstance(chunks, list)
    assert chunks, "the query matched no chunk"
    assert trace["name"] == type(retriever).__name__
    assert trace["chunks"] == [
        f"{chunk.document_id}_{chunk.document_position}" for chunk in chunks
    ]
    return chunks[0]


def test_bm25_finds_the_matching_chunk_and_reloads(tmp_path):
    """A saved BM25 state ranks the same chunk as the retriever that fitted it."""
    fitted = _bm25(tmp_path)
    fitted.init_model()
    fitted.save()

    reloaded = _bm25(tmp_path)
    reloaded.init_model()

    assert _top_chunk(fitted, "stock market").document_position == STOCK_MARKET_POSITION
    assert (
        _top_chunk(reloaded, "stock market").document_position == STOCK_MARKET_POSITION
    )


def test_tfidf_finds_the_matching_chunk_and_reloads(tmp_path):
    """A saved TF-IDF state ranks the same chunk as the retriever that fitted it."""
    fitted = _tfidf(tmp_path)
    fitted.init_model()
    fitted.save()

    reloaded = _tfidf(tmp_path)
    reloaded.init_model()

    assert _top_chunk(fitted, "cats purr").document_position == CATS_POSITION
    assert _top_chunk(reloaded, "cats purr").document_position == CATS_POSITION


def test_saved_row_maps_hold_chunk_ids_not_chunk_text(tmp_path):
    """The persisted row map stores ids, so no chunk text is written twice."""
    for build, folder, file_name in (
        (_bm25, "bm25", "bm25_row_to_chunk_id.pkl"),
        (_tfidf, "tfidf", "matrix_row_to_chunk_id.pkl"),
    ):
        retriever = build(tmp_path)
        retriever.init_model()
        retriever.save()

        with open(tmp_path / folder / file_name, "rb") as f:
            assert pickle.load(f) == {0: 0, 1: 1, 2: 2}


def test_a_reloaded_retriever_returns_the_chunks_it_was_given(tmp_path):
    """Rows resolve through the injected chunks, never through stored objects."""
    for build in (_bm25, _tfidf):
        fitted = build(tmp_path)
        fitted.init_model()
        fitted.save()

        reloaded = build(tmp_path)
        given = reloaded.chunks[1][STOCK_MARKET_POSITION]
        reloaded.init_model()

        assert _top_chunk(reloaded, "stock market") is given


def test_sparse_retrievers_ignore_documents_without_chunks(tmp_path):
    """A document with no chunks neither blocks nor joins the ranking."""
    for name, build in (("bm25", _bm25), ("tfidf", _tfidf)):
        retriever = build(tmp_path / name)
        retriever.chunks = _chunks(with_empty_document=True)
        retriever.init_model()

        top = _top_chunk(retriever, "stock market")

        assert top.document_position == STOCK_MARKET_POSITION
        assert top.document_id == 1
