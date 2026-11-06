"""Deleting a session through the service, including its chat history."""

import uuid

from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
    RAGChunkSet,
    RAGSessionDocument,
)
from DashAI.back.services.RAG.session_document_service import (
    SessionDocumentService,
)
from tests.back.RAG.conftest import _insert_data_document, _insert_rag_session


def _own_chunk_set(db, session_id: int) -> int:
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.commit()
    return chunk_set.id


def _add_chat_history(db, session_id: int) -> int:
    process = GenerativeProcess(session_id=session_id)
    db.add(process)
    db.commit()
    db.refresh(process)
    db.add_all(
        [
            ProcessData(
                data="input",
                data_type="str",
                process_id=process.id,
                is_input=True,
            ),
            ProcessData(
                data="output",
                data_type="str",
                process_id=process.id,
                is_input=False,
            ),
        ]
    )
    db.commit()
    return process.id


def test_delete_a_session_with_chat_history(orm_db, tmp_path):
    session = _insert_rag_session(orm_db, "with-chat")
    session_id = session.id
    document = _insert_data_document(orm_db, tmp_path, "chat.txt", ["hello"])
    process_id = _add_chat_history(orm_db, session_id)
    orm_db.add(RAGSessionDocument(session_id=session_id, data_document_id=document.id))
    orm_db.commit()
    chunk_set_id = _own_chunk_set(orm_db, session_id)

    assert SessionDocumentService(orm_db).delete_session(session_id) is True

    assert orm_db.get(GenerativeSession, session_id) is None
    assert orm_db.get(GenerativeProcess, process_id) is None
    assert orm_db.query(ProcessData).count() == 0
    assert orm_db.get(RAGChunkSet, chunk_set_id) is None
    assert orm_db.get(type(document), document.id) is not None


def test_delete_without_commit_can_be_rolled_back(orm_db, tmp_path):
    session = _insert_rag_session(orm_db, "rollback")
    session_id = session.id
    _insert_data_document(orm_db, tmp_path, "rollback.txt", ["hello"])
    chunk_set_id = _own_chunk_set(orm_db, session_id)

    SessionDocumentService(orm_db).delete_session(session_id, commit=False)
    orm_db.rollback()

    assert orm_db.get(GenerativeSession, session_id) is not None
    assert orm_db.get(RAGChunkSet, chunk_set_id) is not None
