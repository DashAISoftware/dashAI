from typing import Any, Dict, Optional

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.utils import hash_function


def _clean_textract_output(text: str) -> str:
    """Clean textract output by removing control characters and normalizing whitespace."""
    import re

    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class PDFDocument(BaseDocument):
    """
    Class representing a PDF document.
    """

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize the document.
        Args (from database):
            id (int): The unique identifier of the document.
            file_name (str): The name of the file.
            file_path (str): The path to the file.
            created (Optional[str]): The creation date of the document.
            optional_metadata (Optional[Dict[str, Any]]): Additional metadata for the document.
        """
        self.PARSER = kwargs.get("parser", "textract")
        file_hash = hash_function(file_path)
        super().__init__(
            id=id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            created=created,
            optional_metadata=optional_metadata,
        )

    def get_text(self) -> str:
        if self.PARSER == "PyPDF2":
            from PyPDF2 import PdfReader

            reader = PdfReader(self.file_path)
            if not reader.pages:
                raise ValueError(
                    f"The PDF file {self.file_path} is empty or not valid."
                )

            # Extract text from all pages
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
                raise ValueError(
                    f"Error extracting text from PDF file {self.file_path}: {str(e)}"
                )
        else:
            raise ValueError(f"Unsupported parser: {self.PARSER}")

    def get_metadata(self):
        return self.optional_metadata if self.optional_metadata else {}
