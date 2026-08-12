from typing import Any, Dict, Optional

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.exceptions import RAGDocumentParsingError


def _clean_textract_output(text: str) -> str:
    """Clean textract output by removing control characters and normalizing whitespace.

    Args:
        text: Raw text extracted by textract.

    Returns:
        str: Cleaned text with control characters replaced by spaces
            and runs of whitespace collapsed.
    """
    import re

    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class PDFDocument(BaseDocument):
    """Document implementation for PDF files."""

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        file_hash: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
        extractor: Optional[Any] = None,
    ):
        super().__init__(
            id=id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            created=created,
            optional_metadata=optional_metadata,
            extractor=extractor,
        )

    def get_text(self) -> str:
        return self._extract_text(self._default_extract)

    def _default_extract(self) -> str:
        """Fallback extraction using textract (legacy behavior)."""
        import textract

        try:
            text = textract.process(self.file_path, output_encoding="utf-8").decode(
                "utf-8"
            )
            text = _clean_textract_output(text)
            return text.strip()
        except Exception as e:
            raise RAGDocumentParsingError(
                f"Error extracting text from PDF file {self.file_path}: {str(e)}"
            ) from e

    def get_metadata(self) -> Dict[str, Any]:
        base = self.optional_metadata if self.optional_metadata else {}
        base["extractor"] = self.get_extractor_name()
        return base
