"""Regression tests for the dense retriever chunk-id space.

Chunk objects carry two identifiers that differ in production:
``Chunk.id`` is the ordinal of the chunk in its chunk set, while the
``chunks`` dict is keyed by the chunk position inside its document.
Composite retrievers (MMR reranker, sequential, parallel, cross-encoder)
call ``score_chunks`` / ``get_chunk_vectors``
with ``Chunk.id`` values, so the dense retriever must index its
similarity matrix by ``Chunk.id`` and not by the dict key.

These tests build chunks whose ids are offset from their indices so the two
never coincide.
"""

import os

import numpy as np

from DashAI.back.converters.hugging_face.text_embedding import AllMiniLML6V2Embedding
from DashAI.back.converters.hugging_face.text_embedding.base import (
    PASSAGE,
    TextEmbeddingConverter,
)
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
    MMRRerankerRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence import DensePersistence
from tests.back.converters.text_embedding_stub import with_fake_model


def _fake_embedding():
    embedding = AllMiniLML6V2Embedding()
    with_fake_model(embedding)
    return embedding


def _build_chunks(n_chunks: int, doc_id: int = 1, id_offset: int = 500):
    """Return ``{doc_id: {index: Chunk}}`` with DB ids != indices."""
    chunks = {}
    for idx in range(n_chunks):
        chunks[idx] = Chunk(
            id=id_offset + idx,
            document_id=doc_id,
            document_position=idx,
            text=f"chunk {idx} about retrieval augmented generation",
        )
    return {doc_id: chunks}


def _build_dense_retriever(n_chunks: int):
    """Build a DenseEmbeddingRetriever with a persisted embedding matrix."""
    chunks = _build_chunks(n_chunks)
    embedding = _fake_embedding()
    matrix_dir = os.path.join(os.getcwd(), "_tmp_dense_matrix")
    os.makedirs(matrix_dir, exist_ok=True)
    try:
        texts = [chunk.text for chunk in chunks[1].values()]
        np.save(
            os.path.join(matrix_dir, "embeddings.npy"),
            embedding.encode(texts),
        )
        persistence = DensePersistence(
            matrix_dirs={1: matrix_dir}, embedding_model_id=1
        )
        retriever = DenseEmbeddingRetriever(
            embedding_model=embedding,
            similarity_metric="cosine",
            top_k=10,
        )
        retriever.inject_infra(os.path.dirname(matrix_dir), chunks, persistence)
        retriever.embedding_model = embedding
        retriever.init_similarity_matrix()
        return retriever, chunks
    finally:
        os.remove(os.path.join(matrix_dir, "embeddings.npy"))
        os.rmdir(matrix_dir)


class _KeywordEmbedding(TextEmbeddingConverter):
    """Deterministic one-hot embedding converter used to check row alignment.

    It subclasses the real converter because :class:`DenseEmbeddingRetriever`
    accepts nothing else. The pretrained model is never loaded: :meth:`encode`
    is the only surface the retriever calls.
    """

    def __init__(self, words):
        """Store the vocabulary the one-hot vectors are built from.

        Parameters
        ----------
        words : list of str
            One keyword per vector position, in that order.
        """
        super().__init__()
        self.words = list(words)

    def encode(self, texts, role=PASSAGE):
        """Return a one-hot vector per text, keyed on the first matching word.

        Parameters
        ----------
        texts : list of str
            Texts to encode.
        role : str, optional
            ``"passage"`` or ``"query"``; both encode identically here.

        Returns
        -------
        np.ndarray
            ``(len(texts), len(words))`` float array.
        """
        vectors = np.zeros((len(texts), len(self.words)))
        for row, text in enumerate(texts):
            for index, word in enumerate(self.words):
                if word in text:
                    vectors[row, index] = 1.0
                    break
        return vectors


def test_dense_rows_align_with_the_chunks_the_corpus_was_read_in(tmp_path):
    """A shared matrix aligns with the chunks by id, never by their dict key.

    ``ChunkingService.read_chunks`` hands every session its chunks in position
    order, so the matrix another session wrote is in the order this one reads.
    The ids are offset from the positions here, so resolving a row through the
    dict key instead of ``Chunk.id`` cannot pass.
    """
    chunks = {
        1: {
            0: Chunk(100, 1, 0, "zero"),
            1: Chunk(101, 1, 1, "one"),
            2: Chunk(102, 1, 2, "two"),
        }
    }
    embedding = _KeywordEmbedding(["zero", "one", "two"])
    matrix_dir = tmp_path / "dense_matrix"
    matrix_dir.mkdir()
    np.save(
        matrix_dir / "embeddings.npy",
        embedding.encode(["zero", "one", "two"]),
    )
    persistence = DensePersistence(
        matrix_dirs={1: str(matrix_dir)}, embedding_model_id=1
    )
    retriever = DenseEmbeddingRetriever(
        embedding_model=embedding,
        similarity_metric="cosine",
        top_k=1,
    )
    retriever.inject_infra(str(tmp_path), chunks, persistence)
    retriever.embedding_model = embedding
    retriever.init_similarity_matrix()

    results, trace = retriever.retrieve("two")

    assert retriever.matrix_row_to_chunk_id == {0: 100, 1: 101, 2: 102}
    assert results[0].text == "two"
    assert results[0].id == 102
    assert trace["chunks"] == ["1_2"]


def test_dense_retriever_scores_chunks_by_db_id():
    """``score_chunks`` resolves chunk DB ids even when they differ from indices.

    Regression: the similarity matrix was previously keyed by the chunk
    index (dict key) while ``score_chunks`` received ``Chunk.id``, so any
    production DB whose autoincrement ids diverged from chunk positions
    returned an empty score list.
    """
    retriever, _ = _build_dense_retriever(n_chunks=30)

    candidates, _trace = retriever.retrieve("what is machine learning?")
    assert candidates, "retrieve returned no chunks"

    ids = [c.id for c in candidates]
    scored = retriever.score_chunks(ids, "what is machine learning?")
    assert len(scored) == len(ids)
    assert all(cid in ids for cid, _ in scored)


def test_mmr_reranker_returns_chunks_with_dense_child():
    """MMR over a dense child returns chunks in production id space.

    Regression: MMR calls ``child.score_chunks([c.id ...])`` and
    ``child.get_chunk_vectors([c.id ...])``; the dense child returned
    empty scores, so MMR retrieval produced no chunks.
    """
    child, chunks = _build_dense_retriever(n_chunks=30)
    mmr = MMRRerankerRetriever(children=[child], mmr_lambda=0.5, top_k=5)
    mmr.inject_infra(os.getcwd(), chunks, None)

    result, _trace = mmr.retrieve("what is machine learning?")

    assert len(result) == 5
    assert all(c.id is not None for c in result)
