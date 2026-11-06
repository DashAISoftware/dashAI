"""Load and delete the Data module documents a RAG pipeline uses.

Documents are parsed once, when they are uploaded through the Data module,
and their content never changes afterwards. RAG reads that stored content
instead of extracting text again, so every session using a document sees the
same text. Deleting one must also remove the sessions that can no longer work
without it, which is why the lifecycle lives in this same service.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dataloaders.classes.dashai_document import load_document
from DashAI.back.dependencies.database.models import (
    DataDocument,
    GenerativeSession,
    Notebook,
)
from DashAI.back.dependencies.job_queues.base_job_queue import BaseJobQueue
from DashAI.back.models.RAG.documents.source_document import SourceDocument
from DashAI.back.services.RAG.deferred_fs import remove_after_commit
from DashAI.back.services.RAG.session_document_service import (
    SessionDocumentService,
)

log = logging.getLogger(__name__)

_CONTENT_DIRNAME = "document"
_BUSY_STATUSES = (DocumentStatus.DELIVERED, DocumentStatus.STARTED)


class DocumentNotFoundError(LookupError):
    """Raised when the document does not exist."""


class DocumentBusyError(ValueError):
    """Raised while a document is queued or being parsed."""


class DocumentInUseError(ValueError):
    """Raised when sessions use a document and the cascade was not asked for.

    Attributes
    ----------
    sessions : list of GenerativeSession
        Sessions linked to the document.
    notebooks : list of Notebook
        Notebooks that would be deleted with the document.
    """

    def __init__(
        self,
        sessions: List[GenerativeSession],
        notebooks: List[Notebook],
    ) -> None:
        names = ", ".join(session.name for session in sessions)
        super().__init__(
            f"This document is used by these RAG sessions: {names}. "
            "Delete them with it to continue."
        )
        self.sessions = sessions
        self.notebooks = notebooks


class DocumentService:
    """Load parsed Data documents and delete them with their dependants.

    Parameters
    ----------
    db : Session
        Database session. ``load`` only reads it; ``delete`` commits it.
    job_queue : BaseJobQueue, optional
        Queue consulted to stop the deleted sessions' indexing jobs.
    """

    def __init__(self, db: Session, job_queue: Optional[BaseJobQueue] = None) -> None:
        self.db = db
        self._job_queue = job_queue

    def load(self, document_ids: List[int]) -> Dict[int, SourceDocument]:
        """Load the parsed text of several documents.

        Parameters
        ----------
        document_ids : list of int
            ``data_document`` primary keys.

        Returns
        -------
        dict of int to SourceDocument
            One entry per requested document.

        Raises
        ------
        ValueError
            If a document does not exist or has not finished parsing.
        """
        documents: Dict[int, SourceDocument] = {}
        for document_id in document_ids:
            record = self.db.get(DataDocument, document_id)
            if record is None:
                raise ValueError(
                    f"Document with ID {document_id} not found in database."
                )
            if record.status != DocumentStatus.FINISHED:
                raise ValueError(
                    f"Document with ID {document_id} is not ready: its parsing "
                    f"status is {record.status.name}."
                )
            content = load_document(str(Path(record.file_path) / _CONTENT_DIRNAME))
            documents[document_id] = SourceDocument(
                id=record.id, file_name=record.name, content=content
            )
        return documents

    def delete(self, document_id: int, *, cascade_sessions: bool = False) -> None:
        """Delete a document and, optionally, the sessions that use it.

        Parameters
        ----------
        document_id : int
            Primary key of the document.
        cascade_sessions : bool
            Delete the RAG sessions that use the document as well.

        Raises
        ------
        DocumentNotFoundError
            If the document does not exist.
        DocumentBusyError
            If the document is queued or still being parsed.
        DocumentInUseError
            If sessions use it and ``cascade_sessions`` is false.
        """
        document = self.db.get(DataDocument, document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found")

        session_service = SessionDocumentService(self.db, self._job_queue)
        sessions = session_service.sessions_using(document_id)
        if sessions and not cascade_sessions:
            raise DocumentInUseError(sessions, list(document.notebooks))
        if document.status in _BUSY_STATUSES:
            raise DocumentBusyError(
                "The document is still being parsed. Cancel its job before deleting it."
            )

        try:
            if cascade_sessions:
                for session in sessions:
                    session_service.delete_session(session.id, commit=False)
                self.db.flush()
            remove_after_commit(self.db, document.file_path)
            for notebook in document.notebooks:
                remove_after_commit(self.db, notebook.file_path)
            self.db.delete(document)
            self.db.commit()
        except Exception:
            self.db.rollback()
            log.exception("Could not delete document %s", document_id)
            raise
