"""Dense retrievers embed passages and queries with an embedding converter.

``retrieve`` returns ``(chunks, trace)`` for every retriever, so these tests
unpack the tuple instead of treating the return value as a bare chunk list.
"""

import numpy as np

from DashAI.back.converters.hugging_face.text_embedding import (
    MultilingualE5SmallEmbedding,
)
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.persistence import DensePersistence
from tests.back.converters.text_embedding_stub import with_fake_model

DOCUMENT_ID = 1
EMPTY_DOCUMENT_ID = 2
PASSAGE_COUNT = 3
EMBEDDING_MODEL_ID = 1

#: Vector size of the fake sentence model, so no download happens.
FAKE_EMBEDDING_DIM = 8


def _retriever(tmp_path, with_empty_document=False):
    """Build a fitted dense retriever over ``PASSAGE_COUNT`` chunks."""
    embedding = MultilingualE5SmallEmbedding()
    model = with_fake_model(embedding, dim=FAKE_EMBEDDING_DIM)
    chunks = {
        DOCUMENT_ID: {
            index: Chunk(
                id=index,
                document_id=DOCUMENT_ID,
                document_position=index,
                text=f"passage number {index}",
            )
            for index in range(PASSAGE_COUNT)
        }
    }
    matrix_dirs = {DOCUMENT_ID: str(tmp_path / "matrix")}
    if with_empty_document:
        chunks[EMPTY_DOCUMENT_ID] = {}
        matrix_dirs[EMPTY_DOCUMENT_ID] = str(tmp_path / "empty_matrix")
    persistence = DensePersistence(
        matrix_dirs=matrix_dirs, embedding_model_id=EMBEDDING_MODEL_ID
    )
    retriever = DenseEmbeddingRetriever(
        embedding_model=embedding, similarity_metric="cosine", top_k=2
    )
    retriever.inject_infra(str(tmp_path), chunks, persistence)
    retriever.init_model()
    return retriever, model


def test_indexing_encodes_chunks_with_the_passage_role(tmp_path):
    """Indexing encodes every chunk text once, with the passage prompt."""
    _, model = _retriever(tmp_path)

    assert model.calls[0]["prompt"] == "passage: "
    assert model.calls[0]["sentences"] == [
        f"passage number {i}" for i in range(PASSAGE_COUNT)
    ]
    assert np.load(tmp_path / "matrix" / "embeddings.npy").shape == (
        PASSAGE_COUNT,
        FAKE_EMBEDDING_DIM,
    )


def test_dense_retriever_encodes_queries_with_the_query_role(tmp_path):
    """Queries use the query prompt and come back with a trace node."""
    retriever, model = _retriever(tmp_path)

    results, trace = retriever.retrieve("what is passage one")
    scored = retriever.score_chunks([0, 2], "what is passage one")

    assert len(results) == 2
    assert trace["name"] == DenseEmbeddingRetriever.__name__
    assert trace["chunks"] == [
        f"{chunk.document_id}_{chunk.document_position}" for chunk in results
    ]
    assert [call["prompt"] for call in model.calls[1:]] == ["query: ", "query: "]
    assert {chunk_id for chunk_id, _ in scored} == {0, 2}


def test_the_retriever_records_the_converter_and_its_params(tmp_path):
    """The component reference names the converter and its own parameters."""
    retriever, _ = _retriever(tmp_path)

    assert retriever.params["embedding_model"] == {
        "component": "MultilingualE5SmallEmbedding",
        "params": dict(sorted(MultilingualE5SmallEmbedding().params.items())),
    }


def test_documents_without_chunks_do_not_block_indexing(tmp_path):
    """A document with no chunks is skipped, not embedded into an empty matrix."""
    retriever, model = _retriever(tmp_path, with_empty_document=True)

    results, trace = retriever.retrieve("what is passage one")

    assert len(results) == 2
    assert {chunk.document_id for chunk in results} == {DOCUMENT_ID}
    assert len(trace["chunks"]) == len(results)
    assert len(model.calls[0]["sentences"]) == PASSAGE_COUNT
    assert not (tmp_path / "empty_matrix").exists()
