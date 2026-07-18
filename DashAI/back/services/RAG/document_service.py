import logging
import mimetypes
import os
from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.api.api_v1.schemas import DocumentResponse
from DashAI.back.dependencies.database.models import (
    Document as DocumentDBModel,
)
from DashAI.back.dependencies.database.models import (
    GenerativeSession,
)
from DashAI.back.models.RAG.documents import (
    BaseDocument,
    DocumentFileType,
    PDFDocument,
    TxtDocument,
)
from DashAI.back.models.RAG.exceptions import RAGDocumentFileTypeError
from DashAI.back.models.RAG.utils import hash_function

log = logging.getLogger(__name__)

_DOCUMENT_CLASSES: dict[DocumentFileType, type[BaseDocument]] = {
    DocumentFileType.TXT: TxtDocument,
    DocumentFileType.PDF: PDFDocument,
    DocumentFileType.MD: TxtDocument,
    DocumentFileType.RST: TxtDocument,
    DocumentFileType.TEX: TxtDocument,
    # CSV, MD, RST, TEX are parsed as plain text via TxtDocument.
    # This is a limitation: CSV files are structured data, not free text.
    # A future improvement would add a dedicated CsvDocument parser.
    DocumentFileType.CSV: TxtDocument,
}


class DocumentService:
    """Service layer for document CRUD, file storage, and hydration."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_response(
        self, doc: DocumentDBModel, base_url: str = ""
    ) -> DocumentResponse:
        return DocumentResponse(
            id=doc.id,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_hash=doc.file_hash,
            created=doc.created,
            last_modified=doc.last_modified,
            optional_metadata=doc.optional_metadata,
            related_sessions=[s.id for s in doc.get_related_sessions]
            if doc.get_related_sessions
            else None,
            file_url=f"{base_url}/api/v1/document/{doc.id}/download",
        )

    def _get_document_or_raise(self, document_id: int) -> DocumentDBModel:
        doc = self.db.get(DocumentDBModel, document_id)
        if doc is None:
            raise ValueError(f"Document with ID {document_id} does not exist.")
        return doc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(
        self,
        file_content: bytes,
        file_name: str,
        file_type: str | DocumentFileType,
        docs_path: str,
        optional_metadata: dict = None,
    ) -> DocumentResponse:
        """Upload a document.

        Handles hash deduplication, file storage, and DB record creation.

        Parameters
        ----------
        file_content : bytes
            Raw file bytes.
        file_name : str
            Original file name.
        file_type : str | DocumentFileType
            File extension / type, e.g. ``DocumentFileType.PDF`` or ``"pdf"``.
        docs_path : str
            Directory on disk where the file will be written.
        optional_metadata : dict, optional
            Arbitrary metadata attached to the document.

        Returns
        -------
        DocumentResponse
            The created or updated document representation.

        Raises
        ------
        ValueError
            If ``docs_path`` does not exist or a database error occurs.
        """
        if isinstance(file_type, DocumentFileType):
            file_type = file_type.value
        if not os.path.isdir(docs_path):
            raise ValueError(f"Documents folder does not exist: {docs_path}")

        optional_metadata = optional_metadata or {}
        file_content_hash = hash_function(file_content)
        file_path = os.path.join(docs_path, file_name)

        try:
            existing = (
                self.db.query(DocumentDBModel)
                .filter_by(file_hash=file_content_hash)
                .first()
            )
            if existing:
                existing.file_name = file_name
                existing.file_path = file_path
                existing.optional_metadata = optional_metadata
                self.db.commit()
                return self._to_response(existing)

            with open(file_path, "wb") as f:
                f.write(file_content)

            doc = DocumentDBModel(
                file_name=file_name,
                file_type=file_type,
                file_path=file_path,
                file_hash=file_content_hash,
                optional_metadata=optional_metadata or None,
            )
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)
            return self._to_response(doc)

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error during document upload.") from e

    def get(self, document_id: int) -> DocumentResponse:
        """Get document metadata by ID.

        Parameters
        ----------
        document_id : int

        Returns
        -------
        DocumentResponse

        Raises
        ------
        ValueError
            If the document does not exist.
        """
        try:
            doc = self._get_document_or_raise(document_id)
            return self._to_response(doc)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error retrieving document.") from e

    def get_all(self, base_url: str = "") -> List[DocumentResponse]:
        """Get all documents with ``file_url`` included.

        Parameters
        ----------
        base_url : str
            Base URL prefix for download links.

        Returns
        -------
        list[DocumentResponse]
        """
        try:
            docs: List[DocumentDBModel] = self.db.query(DocumentDBModel).all()
            return [self._to_response(d, base_url) for d in docs]
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error listing documents.") from e

    def get_by_session(
        self, session_id: int, base_url: str = ""
    ) -> List[DocumentResponse]:
        """Get documents linked to a generative session.

        Documents are identified from ``session.parameters["documents"]``.

        Parameters
        ----------
        session_id : int
        base_url : str

        Returns
        -------
        list[DocumentResponse]
        """
        try:
            session = self.db.get(GenerativeSession, session_id)
            if session is None:
                raise ValueError(f"GenerativeSession with ID {session_id} not found.")

            document_ids: List[int] = session.parameters.get("documents", [])
            if not document_ids:
                return []

            docs = (
                self.db.query(DocumentDBModel)
                .filter(DocumentDBModel.id.in_(document_ids))
                .all()
            )
            return [self._to_response(d, base_url) for d in docs]

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error retrieving session documents.") from e

    def delete(self, document_id: int) -> None:
        """Delete a document file from disk and its DB record.

        Parameters
        ----------
        document_id : int

        Raises
        ------
        ValueError
            If the document does not exist.
        """
        try:
            doc = self._get_document_or_raise(document_id)

            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)

            self.db.delete(doc)
            self.db.commit()

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error deleting document.") from e
        except OSError as e:
            log.exception(e)
            raise ValueError("Error deleting physical file.") from e

    def update_metadata(
        self,
        document_id: int,
        file_name: str = None,
        optional_metadata: dict = None,
    ) -> DocumentResponse:
        """Update document metadata (``file_name``, ``optional_metadata``).

        Parameters
        ----------
        document_id : int
        file_name : str, optional
            New file name.  Also updates ``file_type`` from the extension.
        optional_metadata : dict, optional

        Returns
        -------
        DocumentResponse

        Raises
        ------
        ValueError
            If the document does not exist.
        """
        try:
            doc = self._get_document_or_raise(document_id)

            if file_name is not None:
                doc.file_name = file_name
                ext = os.path.splitext(file_name)[1].lstrip(".")
                try:
                    doc.file_type = DocumentFileType(ext).value
                except ValueError as err:
                    raise RAGDocumentFileTypeError(
                        f"Unsupported file type: {ext}"
                    ) from err

            if optional_metadata is not None:
                doc.optional_metadata = optional_metadata

            doc.last_modified = datetime.now()
            self.db.commit()
            self.db.refresh(doc)
            return self._to_response(doc)

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error updating document metadata.") from e

    def download(self, document_id: int) -> Tuple[bytes, str, str]:
        """Return file content, media type, and filename for download.

        Parameters
        ----------
        document_id : int

        Returns
        -------
        tuple[bytes, str, str]
            ``(file_content, media_type, filename)``.

        Raises
        ------
        ValueError
            If the document or its physical file is not found.
        """
        try:
            doc = self._get_document_or_raise(document_id)

            if not os.path.exists(doc.file_path):
                raise ValueError(f"File not found on disk: {doc.file_path}")

            ext = os.path.splitext(doc.file_name)[1].lower()
            media_type, _ = mimetypes.guess_type(doc.file_name)
            if media_type is None:
                media_type = {
                    ".txt": "text/plain",
                    ".pdf": "application/pdf",
                }.get(ext, "application/octet-stream")

            with open(doc.file_path, "rb") as f:
                content = f.read()

            return content, media_type, doc.file_name

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error during document download.") from e

    def load(self, document_ids: List[int]) -> Dict[int, BaseDocument]:
        """Load and hydrate DB document rows into ``BaseDocument`` instances.

        Parameters
        ----------
        document_ids : list[int]

        Returns
        -------
        dict[int, BaseDocument]
            Mapping from document ID to hydrated document object.

        Raises
        ------
        ValueError
            If any document ID is not found or the file type is unsupported.
        """
        documents: Dict[int, BaseDocument] = {}
        for doc_id in document_ids:
            db_doc: DocumentDBModel = (
                self.db.query(DocumentDBModel)
                .filter(DocumentDBModel.id == doc_id)
                .first()
            )
            if db_doc is None:
                raise ValueError(f"Document with ID {doc_id} not found in database.")
            try:
                doc_class = _DOCUMENT_CLASSES[DocumentFileType(db_doc.file_type)]
            except (KeyError, ValueError) as err:
                supported = ", ".join(e.value for e in DocumentFileType)
                raise ValueError(
                    f"Unsupported file type '{db_doc.file_type}'. "
                    f"Supported types: {supported}."
                ) from err
            documents[doc_id] = doc_class(
                id=db_doc.id,
                file_name=db_doc.file_name,
                file_path=db_doc.file_path,
                file_hash=db_doc.file_hash,
                created=db_doc.created,
                optional_metadata=db_doc.optional_metadata,
            )
        return documents

    def validate_exist(self, document_ids: List[int]) -> None:
        """Raise ``ValueError`` if any document ID does not exist in the DB.

        Parameters
        ----------
        document_ids : list[int]

        Raises
        ------
        ValueError
            If one or more document IDs are not found.
        """
        existing = (
            self.db.query(DocumentDBModel.id)
            .filter(DocumentDBModel.id.in_(document_ids))
            .all()
        )
        existing_ids = {row.id for row in existing}
        missing = [str(i) for i in document_ids if i not in existing_ids]
        if missing:
            raise ValueError(f"Documents with IDs {', '.join(missing)} not found.")

    def get_related_sessions(self, document_id: int) -> List[int]:
        """Get session IDs linked to a document.

        Parameters
        ----------
        document_id : int

        Returns
        -------
        list[int]
            Session IDs related to the document.

        Raises
        ------
        ValueError
            If the document is not found.
        """
        try:
            doc = self._get_document_or_raise(document_id)
            if not doc.get_related_sessions:
                return []
            return [s.id for s in doc.get_related_sessions]
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise ValueError("Database error retrieving related sessions.") from e
