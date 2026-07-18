from typing import Any, Dict, Optional

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.exceptions import RAGDocumentParsingError


class TxtDocument(BaseDocument):
    """Document implementation for plain text (.txt) files.

    Reads text content directly from the file system with UTF-8 encoding.
    """

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        file_hash: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a TxtDocument instance.

        Args:
            id: The unique identifier of the document.
            file_name: The name of the file.
            file_path: The path to the file.
            file_hash: A hash of the file content (computed upstream).
            created: The creation date of the document.
            optional_metadata: Additional metadata for the document.
        """
        super().__init__(
            id=id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            created=created,
            optional_metadata=optional_metadata,
        )

    def get_text(self) -> str:
        """Read and return the text content of the document.

        Returns:
            str: The text content of the document with leading/trailing
                whitespace removed.

        Raises:
            RAGDocumentParsingError: If the file is not found, cannot be
                read, or contains invalid UTF-8 encoding.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError as e:
            raise RAGDocumentParsingError(f"File not found: {self.file_path}") from e
        except IOError as e:
            raise RAGDocumentParsingError(
                f"Error reading file {self.file_path}: {str(e)}"
            ) from e
        except UnicodeDecodeError as e:
            raise RAGDocumentParsingError(
                f"Encoding error reading file {self.file_path}: {str(e)}"
            ) from e
        return text.strip()

    def get_metadata(self) -> Dict[str, Any]:
        """Get the optional metadata associated with the document.

        Returns:
            Dict[str, Any]: The metadata dictionary, or an empty dict
                if no metadata was provided.
        """
        return self.optional_metadata if self.optional_metadata else {}
