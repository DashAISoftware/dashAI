from typing import Any, Dict, Optional

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.utils import hash_function


class TxtDocument(BaseDocument):
    """
    Class representing a .txt document.
    """

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the document.
        Args (from database):
            id (int): The unique identifier of the document.
            file_name (str): The name of the file.
            file_path (str): The path to the file.
            file_hash (str): A hash of the file content.
            created (Optional[str]): The creation date of the document.
            optional_metadata (Optional[Dict[str, Any]]): Additional metadata for the document.
        """
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
        """
        Get the text content of the document.

        Returns:
            str: The text content of the document.
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return text.strip()

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the metadata of the document.

        Returns:
            Dict[str, Any]: The metadata of the document.
        """
        return self.optional_metadata if self.optional_metadata else {}
