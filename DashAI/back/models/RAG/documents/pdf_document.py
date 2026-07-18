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
    """Document implementation for PDF files.

    Supports two text-extraction backends: PyPDF2 and textract.
    """

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        file_hash: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
        parser: str = "textract",
    ):
        """Initialize a PDFDocument instance.

        Args:
            id: The unique identifier of the document.
            file_name: The name of the file.
            file_path: The path to the file.
            file_hash: A hash of the file content (computed upstream).
            created: The creation date of the document.
            optional_metadata: Additional metadata for the document.
            parser: PDF parser to use ("PyPDF2" or "textract").

        Raises:
            ValueError: If the parser is not "PyPDF2" or "textract".
        """
        if parser not in ("PyPDF2", "textract"):
            raise ValueError(
                f"Unsupported parser '{parser}'. Must be 'PyPDF2' or 'textract'."
            )
        self.PARSER = parser
        super().__init__(
            id=id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            created=created,
            optional_metadata=optional_metadata,
        )

    def get_text(self) -> str:
        """Extract and return the text content of the PDF document.

        Uses either PyPDF2 or textract depending on the chosen parser.

        Returns:
            str: The extracted text with leading/trailing whitespace removed.

        Raises:
            ValueError: If the PDF file is empty or the parser is unsupported.
            RAGDocumentParsingError: If text extraction with textract fails.
        """
        if self.PARSER == "PyPDF2":
            from PyPDF2 import PdfReader

            reader = PdfReader(self.file_path)
            if not reader.pages:
                raise ValueError(
                    f"The PDF file {self.file_path} is empty or not valid."
                )

            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            return text.strip()
        elif self.PARSER == "textract":
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
        else:
            raise ValueError(f"Unsupported parser: {self.PARSER}")

    def get_metadata(self) -> Dict[str, Any]:
        """Get the optional metadata associated with the document.

        Returns:
            Dict[str, Any]: The metadata dictionary, or an empty dict
                if no metadata was provided.
        """
        return self.optional_metadata if self.optional_metadata else {}
