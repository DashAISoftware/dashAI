"""Loads Document rows from the database and hydrates in-memory
BaseDocument instances.  Keeps the pipeline constructor free of raw
SQL queries.
"""

from typing import Dict, List

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import Document as DBDocument
from DashAI.back.models.RAG.documents import BaseDocument, PDFDocument, TxtDocument

_DOCUMENT_CLASSES: Dict[str, type[BaseDocument]] = {
    "txt": TxtDocument,
    "pdf": PDFDocument,
    "md": TxtDocument,
    "rst": TxtDocument,
    "tex": TxtDocument,
    "csv": TxtDocument,
}


class DocumentLoader:
    """Resolves a list of document IDs to in-memory BaseDocument objects."""

    def __init__(self, db: Session):
        self.db = db

    def load(self, document_ids: List[int]) -> Dict[int, BaseDocument]:
        """Load and hydrate documents.

        Parameters
        ----------
        document_ids : list[int]
            IDs present in the ``document`` table.

        Returns
        -------
        dict[int, BaseDocument]
            Mapping from document ID to the hydrated document object.

        Raises
        ------
        ValueError
            If any document ID is not found in the database.
        """
        documents: Dict[int, BaseDocument] = {}
        for doc_id in document_ids:
            db_doc: DBDocument | None = (
                self.db.query(DBDocument).filter(DBDocument.id == doc_id).first()
            )
            if db_doc is None:
                raise ValueError(f"Document with ID {doc_id} not found in database.")
            try:
                doc_class = _DOCUMENT_CLASSES[db_doc.file_type]
            except KeyError as err:
                raise ValueError(
                    f"Unsupported file type '{db_doc.file_type}'. "
                    f"Supported types: txt, pdf, md, rst, tex, csv."
                ) from err
            documents[doc_id] = doc_class(
                id=db_doc.id,
                file_name=db_doc.file_name,
                file_path=db_doc.file_path,
                created=db_doc.created,
                optional_metadata=db_doc.optional_metadata,
            )
        return documents
