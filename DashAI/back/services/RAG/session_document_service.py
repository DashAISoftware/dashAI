"""Which Data module documents a RAG session uses.

A ``DataDocument`` belongs to the Data module. Several sessions may use it and
none may change it, so a session only holds links (``rag_session_document``).
Attaching or detaching changes those links and discards the indexes the
session built over its previous set of documents, never the document itself
nor another session's index.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dependencies.database.models import (
    DataDocument,
    GenerativeProcess,
    GenerativeSession,
    GenerativeSessionParameterHistory,
    ProcessData,
    RAGPipeline,
    RAGSessionDocument,
)
from DashAI.back.dependencies.job_queues.base_job_queue import BaseJobQueue
from DashAI.back.models.RAG.RAG_constants import RAG_PARAM_DOCUMENTS
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.index_job_service import cancel_live_index_job

log = logging.getLogger(__name__)

_RAG_TASK_NAME = "RAGTask"


@dataclass(frozen=True)
class SessionRef:
    """A session's id and name, as document payloads expose them."""

    id: int
    name: str


class DocumentNotReadyError(ValueError):
    """Raised when a document still being parsed is attached to a session."""


class SessionDocumentService:
    """Attach, detach and list the Data documents of RAG sessions, and delete
    the sessions themselves with their RAG artifacts.

    Parameters
    ----------
    db : Session
        Database session; ``attach`` and ``detach`` commit it.
    job_queue : BaseJobQueue, optional
        Queue holding the sessions' indexing jobs. A live job is cancelled
        before the documents it indexes change; ``None`` skips that.
    """

    def __init__(self, db: Session, job_queue: Optional[BaseJobQueue] = None):
        self.db = db
        self._job_queue = job_queue

    def get_rag_session(self, session_id: int) -> GenerativeSession:
        """Return a RAG session or raise.

        Parameters
        ----------
        session_id : int
            The session to look up.

        Returns
        -------
        GenerativeSession
            The session.

        Raises
        ------
        LookupError
            If the session does not exist.
        ValueError
            If the session is not a RAG session.
        """
        session = self.db.get(GenerativeSession, session_id)
        if session is None:
            raise LookupError(f"Generative session {session_id} does not exist.")
        if session.task_name != _RAG_TASK_NAME:
            raise ValueError(
                f"Session {session_id} is a '{session.task_name}' session; only "
                "RAG sessions use documents."
            )
        return session

    def list_documents(self, session_id: int) -> List[DataDocument]:
        """Return the documents a session uses, by id.

        Parameters
        ----------
        session_id : int
            The RAG session.

        Returns
        -------
        list of DataDocument
            The linked documents.
        """
        session = self.get_rag_session(session_id)
        return (
            self.db.query(DataDocument)
            .join(
                RAGSessionDocument,
                RAGSessionDocument.data_document_id == DataDocument.id,
            )
            .filter(RAGSessionDocument.session_id == session.id)
            .order_by(DataDocument.id)
            .all()
        )

    def attach(
        self, session_id: int, data_document_ids: List[int]
    ) -> List[DataDocument]:
        """Link documents to a session; already linked ones are skipped.

        Parameters
        ----------
        session_id : int
            The RAG session.
        data_document_ids : list of int
            Documents to attach. Duplicates are ignored.

        Returns
        -------
        list of DataDocument
            Every document the session uses afterwards.

        Raises
        ------
        LookupError
            If the session or a document does not exist.
        DocumentNotReadyError
            If a document has not finished parsing.
        """
        session = self.get_rag_session(session_id)
        requested = list(dict.fromkeys(data_document_ids))
        found = {
            document.id: document
            for document in self.db.query(DataDocument)
            .filter(DataDocument.id.in_(requested))
            .all()
        }
        missing = [str(i) for i in requested if i not in found]
        if missing:
            raise LookupError(f"Documents with IDs {', '.join(missing)} not found.")
        pending = [
            found[i].name
            for i in requested
            if found[i].status != DocumentStatus.FINISHED
        ]
        if pending:
            raise DocumentNotReadyError(
                f"These documents are still being processed: {', '.join(pending)}."
            )
        linked = set(self.linked_document_ids(session.id))
        new_ids = [i for i in requested if i not in linked]
        if new_ids:
            self._discard_indexes(session)
            for document_id in new_ids:
                self.db.add(
                    RAGSessionDocument(
                        session_id=session.id, data_document_id=document_id
                    )
                )
            self.sync_session_documents(session)
            self.db.commit()
        return self.list_documents(session.id)

    def detach(self, session_id: int, data_document_id: int) -> None:
        """Unlink a document from a session; the document stays in Data.

        Parameters
        ----------
        session_id : int
            The RAG session.
        data_document_id : int
            The document to detach.

        Raises
        ------
        LookupError
            If the session does not exist or does not use the document.
        """
        session = self.get_rag_session(session_id)
        link = (
            self.db.query(RAGSessionDocument)
            .filter_by(session_id=session.id, data_document_id=data_document_id)
            .one_or_none()
        )
        if link is None:
            raise LookupError(
                f"Document {data_document_id} is not attached to session {session_id}."
            )
        self._discard_indexes(session)
        self.db.delete(link)
        self.sync_session_documents(session)
        self.db.commit()

    def delete_session(
        self,
        session_id: int,
        *,
        commit: bool = True,
        missing_ok: bool = False,
    ) -> bool:
        """Delete a session, its processes and its RAG artifacts.

        SQLite foreign keys are not enforced, so every dependant row is
        deleted explicitly: process data, processes, parameter history,
        document links, chunk sets and the ``rag_pipeline`` row.

        Parameters
        ----------
        session_id : int
            The session to delete.
        commit : bool
            Commit when done. ``False`` lets a caller delete several sessions
            and their shared document in one transaction.
        missing_ok : bool
            Return ``False`` instead of raising when the session does not
            exist. The bulk endpoint uses this to skip unknown ids.

        Returns
        -------
        bool
            Whether a session was found and deleted.

        Raises
        ------
        LookupError
            If the session does not exist and ``missing_ok`` is false.
        """
        session = self.db.get(GenerativeSession, session_id)
        if session is None:
            if missing_ok:
                return False
            raise LookupError(f"Generative session {session_id} does not exist.")

        old_parameters = dict(session.parameters or {})
        try:
            # Stop work that would otherwise keep writing the rows deleted
            # below. The pointer is cleared with the same transaction.
            cancel_live_index_job(session, self._job_queue)
            self._delete_processes(session_id)
            CleanupService(self.db).invalidate_session_artifacts(
                session_id, commit=False
            )
            self._delete_history(session_id)
            self._delete_document_links(session_id)
            # The bulk delete above bypasses the identity map. If the
            # collection had been loaded, the session's delete-orphan cascade
            # would otherwise try to delete those rows a second time.
            self.db.expire(session, ["document_links"])

            # Runs while the pipeline still exists: it looks the pipeline up
            # to know which retriever and chunking rows belong to the session.
            CleanupService(self.db).cleanup_orphaned_resources(
                session_id, old_parameters, commit=False
            )
            # SQLite will not cascade this, and leaving it behind would make
            # the next session that reuses the id inherit a stale pipeline.
            self.db.query(RAGPipeline).filter(
                RAGPipeline.session_id == session_id
            ).delete(synchronize_session="fetch")

            self.db.delete(session)
            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            log.exception("Could not delete generative session %s", session_id)
            raise
        return True

    def sessions_using(self, data_document_id: int) -> List[GenerativeSession]:
        """Return the sessions that use a document, by id.

        Parameters
        ----------
        data_document_id : int
            The document.

        Returns
        -------
        list of GenerativeSession
            Sessions linked to it.
        """
        return (
            self.db.query(GenerativeSession)
            .join(
                RAGSessionDocument,
                RAGSessionDocument.session_id == GenerativeSession.id,
            )
            .filter(RAGSessionDocument.data_document_id == data_document_id)
            .order_by(GenerativeSession.id)
            .all()
        )

    def sessions_by_document(self) -> Dict[int, List[SessionRef]]:
        """Map every document id to the sessions that use it.

        Returns
        -------
        dict
            ``{document_id: [SessionRef(id, name)]}``. Documents without
            sessions are absent.
        """
        rows = (
            self.db.query(RAGSessionDocument.data_document_id, GenerativeSession)
            .join(
                GenerativeSession,
                GenerativeSession.id == RAGSessionDocument.session_id,
            )
            .order_by(GenerativeSession.id)
            .all()
        )
        usage: Dict[int, List[SessionRef]] = {}
        for document_id, session in rows:
            usage.setdefault(document_id, []).append(
                SessionRef(id=session.id, name=session.name)
            )
        return usage

    def linked_document_ids(self, session_id: int) -> List[int]:
        """Return the ids of the documents a session uses, ascending.

        Parameters
        ----------
        session_id : int
            The session.

        Returns
        -------
        list of int
            ``data_document`` ids.
        """
        return [
            row[0]
            for row in self.db.query(RAGSessionDocument.data_document_id)
            .filter(RAGSessionDocument.session_id == session_id)
            .order_by(RAGSessionDocument.data_document_id)
            .all()
        ]

    def sync_session_documents(self, session: GenerativeSession) -> None:
        """Rebuild ``parameters["documents"]`` from the session's links.

        The links are the authority. The list is what the pipeline config, the
        indexing job, the chat guard and the parameter history read; the
        history is how the index status tells a stale index from a new one.
        Adds a history entry when the list changes. Does not commit.

        Parameters
        ----------
        session : GenerativeSession
            The session to update.
        """
        self.db.flush()
        document_ids = self.linked_document_ids(session.id)
        parameters = dict(session.parameters or {})
        if parameters.get(RAG_PARAM_DOCUMENTS) == document_ids:
            return
        parameters[RAG_PARAM_DOCUMENTS] = document_ids
        session.parameters = parameters
        self.db.add(
            GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=parameters,
                model_name=session.model_name,
            )
        )

    def _discard_indexes(self, session: GenerativeSession) -> None:
        """Stop the session's live index and queue its chunk sets for deletion.

        Parameters
        ----------
        session : GenerativeSession
            The session whose documents are about to change.
        """
        cancel_live_index_job(session, self._job_queue)
        CleanupService(self.db).invalidate_session_artifacts(session.id, commit=False)

    def _delete_processes(self, session_id: int) -> None:
        """Delete a session's processes and their input/output rows."""
        processes = (
            self.db.query(GenerativeProcess)
            .filter(GenerativeProcess.session_id == session_id)
            .all()
        )
        for process in processes:
            # ``fetch`` keeps the identity map in sync with the loaded
            # process.input/output collections; ``False`` leaves stale
            # ProcessData objects that the later ``delete(process)`` tries to
            # nullify, raising StaleDataError.
            self.db.query(ProcessData).filter(
                ProcessData.process_id == process.id
            ).delete(synchronize_session="fetch")
        for process in processes:
            self.db.delete(process)

    def _delete_history(self, session_id: int) -> None:
        """Delete a session's parameter history."""
        self.db.query(GenerativeSessionParameterHistory).filter(
            GenerativeSessionParameterHistory.session_id == session_id
        ).delete(synchronize_session="fetch")

    def _delete_document_links(self, session_id: int) -> None:
        """Delete the session's links to Data documents.

        The documents themselves belong to the Data module and stay. The
        links must go before the document-delete cascade reaches the same
        rows, and before the session's ``delete-orphan`` cascade tries to
        delete them a second time.
        """
        self.db.query(RAGSessionDocument).filter(
            RAGSessionDocument.session_id == session_id
        ).delete(synchronize_session="fetch")
        self.db.flush()
