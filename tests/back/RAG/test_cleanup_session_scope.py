"""Index cleanup never leaves the session it was asked to clean."""

import uuid

from DashAI.back.dependencies.database.models import Chunk as ChunkRow
from DashAI.back.dependencies.database.models import (
    RAGChunkSet,
    RAGChunkSetDocument,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.services.RAG.cleanup_service import CleanupService
from tests.back.RAG.conftest import _insert_data_document, _insert_rag_session


def _chunk_set_with_sparse_index(db, session_id, document_id, storage) -> int:
    """Insert a chunk set with one chunk and a fitted sparse retriever.

    Parameters
    ----------
    db : Session
        Database session to write with.
    session_id : int or None
        Owning session, None for a legacy chunk set.
    document_id : int
        Document the chunk belongs to.
    storage : pathlib.Path
        Folder created as the retriever storage.

    Returns
    -------
    int
        The chunk set id.
    """
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.flush()
    db.add(RAGChunkSetDocument(chunk_set_id=chunk_set.id, document_id=document_id))
    db.add(
        ChunkRow(
            chunk_set_id=chunk_set.id, document_id=document_id, chunk_index=0, text="t"
        )
    )
    pipeline = RAGPipeline(
        session_id=session_id if session_id is not None else 0, name=""
    )
    db.add(pipeline)
    db.flush()
    bridge = RAGRetriever(class_name="BM25Retriever", pipeline_id=pipeline.id)
    db.add(bridge)
    db.flush()
    storage.mkdir(parents=True, exist_ok=True)
    db.add(
        RAGSparseRetriever(
            bridge_id=bridge.id,
            chunk_set_id=chunk_set.id,
            class_name="BM25Retriever",
            parameters={},
            storage_folder=str(storage),
        )
    )
    db.commit()
    return chunk_set.id


def test_invalidating_a_session_leaves_other_sessions_alone(orm_db, tmp_path):
    first = _insert_rag_session(orm_db, "scope_a")
    second = _insert_rag_session(orm_db, "scope_b")
    document = _insert_data_document(orm_db, tmp_path / "docs", "shared.txt", ["s"])
    first_set = _chunk_set_with_sparse_index(
        orm_db, first.id, document.id, tmp_path / "a"
    )
    second_set = _chunk_set_with_sparse_index(
        orm_db, second.id, document.id, tmp_path / "b"
    )

    CleanupService(orm_db).invalidate_session_artifacts(first.id)

    assert orm_db.get(RAGChunkSet, first_set) is None
    assert orm_db.query(ChunkRow).filter_by(chunk_set_id=first_set).count() == 0
    assert orm_db.get(RAGChunkSet, second_set) is not None
    assert orm_db.query(ChunkRow).filter_by(chunk_set_id=second_set).count() == 1
    assert not (tmp_path / "a").exists()
    assert (tmp_path / "b").exists()


def test_legacy_chunk_sets_are_the_ones_without_a_session(orm_db, tmp_path):
    owner = _insert_rag_session(orm_db, "scope_owner")
    document = _insert_data_document(orm_db, tmp_path / "docs", "c.txt", ["c"])
    legacy_set = _chunk_set_with_sparse_index(
        orm_db, None, document.id, tmp_path / "legacy"
    )
    owned_set = _chunk_set_with_sparse_index(
        orm_db, owner.id, document.id, tmp_path / "owned"
    )

    assert CleanupService(orm_db).invalidate_legacy_artifacts() == 1

    assert orm_db.get(RAGChunkSet, legacy_set) is None
    assert orm_db.get(RAGChunkSet, owned_set) is not None
    assert not (tmp_path / "legacy").exists()
    assert (tmp_path / "owned").exists()


def test_a_shared_sparse_folder_survives_until_the_last_reference(orm_db, tmp_path):
    """Content-addressed folders are only removed with their last row."""
    first = _insert_rag_session(orm_db, "shared_sparse_a")
    second = _insert_rag_session(orm_db, "shared_sparse_b")
    document = _insert_data_document(orm_db, tmp_path / "docs", "shared.txt", ["s"])
    storage = tmp_path / "shared_sparse"
    first_set = _chunk_set_with_sparse_index(orm_db, first.id, document.id, storage)
    second_set = _chunk_set_with_sparse_index(orm_db, second.id, document.id, storage)
    service = CleanupService(orm_db)

    service.invalidate_session_artifacts(first.id)

    assert orm_db.get(RAGChunkSet, first_set) is None
    assert orm_db.query(RAGSparseRetriever).count() == 1
    assert storage.exists(), "the folder is still referenced by the second session"

    service.invalidate_session_artifacts(second.id)

    assert orm_db.get(RAGChunkSet, second_set) is None
    assert orm_db.query(RAGSparseRetriever).count() == 0
    assert not storage.exists(), "the last reference released the folder"


def test_composite_cleanup_keeps_a_shared_sparse_folder(orm_db, tmp_path):
    """A composite's child must not delete another session's shared folder."""
    first = _insert_rag_session(orm_db, "shared_composite_a")
    second = _insert_rag_session(orm_db, "shared_composite_b")
    document = _insert_data_document(orm_db, tmp_path / "docs", "shared.txt", ["s"])
    storage = tmp_path / "shared_composite_sparse"
    first_set = _chunk_set_with_sparse_index(orm_db, first.id, document.id, storage)
    _chunk_set_with_sparse_index(orm_db, second.id, document.id, storage)

    detail = orm_db.query(RAGSparseRetriever).filter_by(chunk_set_id=first_set).one()
    child_bridge = orm_db.get(RAGRetriever, detail.bridge_id)
    parent = RAGRetriever(
        class_name="ParallelRetriever", pipeline_id=child_bridge.pipeline_id
    )
    orm_db.add(parent)
    orm_db.flush()
    orm_db.add(
        RAGRetrieverChild(parent_id=parent.id, child_id=child_bridge.id, child_order=0)
    )
    orm_db.commit()

    CleanupService(orm_db)._cleanup_composite_retriever(
        {"retriever_model": {"component": "ParallelRetriever"}}, first.id
    )
    orm_db.flush()

    assert orm_db.get(RAGRetriever, parent.id) is None
    assert orm_db.query(RAGSparseRetriever).count() == 1
    assert storage.exists(), "the second session still references the folder"


def _embedding_matrix_state(db, session_id, document_id, storage) -> list:
    """Insert one embedding model and two matrix rows sharing one folder."""
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    other_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(other_set)
    db.flush()
    model = RAGEmbeddingModel(class_name="SentenceTransformerEmbedding", parameters={})
    db.add(model)
    db.flush()
    storage.mkdir(parents=True, exist_ok=True)
    first = RAGEmbeddingMatrix(
        document_id=document_id,
        chunk_set_id=chunk_set.id,
        embedding_model_id=model.id,
        storage_folder=str(storage),
        matrix_shape=[2, 4],
    )
    second = RAGEmbeddingMatrix(
        document_id=document_id,
        chunk_set_id=other_set.id,
        embedding_model_id=model.id,
        storage_folder=str(storage),
        matrix_shape=[2, 4],
    )
    db.add_all([first, second])
    db.commit()
    return [first, second]


def test_a_shared_embedding_folder_survives_until_the_last_row(orm_db, tmp_path):
    """The folder guard reports a live reference until every row is excluded."""
    session = _insert_rag_session(orm_db, "shared_dense")
    document = _insert_data_document(orm_db, tmp_path / "docs", "dense.txt", ["d"])
    storage = tmp_path / "shared_embeddings"
    first, second = _embedding_matrix_state(orm_db, session.id, document.id, storage)
    service = CleanupService(orm_db)

    assert service._embedding_folder_in_use(str(storage), exclude_ids=[first.id])
    assert not service._embedding_folder_in_use(
        str(storage), exclude_ids=[first.id, second.id]
    )
    assert not service._embedding_folder_in_use(str(tmp_path / "unused"))
