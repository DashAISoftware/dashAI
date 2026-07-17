from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseDocument(ABC):
    """
    Base class for documents.
    """

    SUPPORTED_FILE_TYPES = ["pdf", "txt"]

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        file_hash: str,
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
            optional_metadata (Optional[Dict[str, Any]]): Additional
                metadata for the document.
        """
        self.id = id
        self.file_name = file_name
        self.file_path = file_path
        self.file_hash = file_hash
        self.created = created if created else None
        self.optional_metadata = optional_metadata if optional_metadata else None

    @abstractmethod
    def get_text(self) -> str:
        """
        Get the text content of the document.

        Returns:
            str: The text content of the document.
        """

    def get_text_length(self) -> int:
        """
        Get the length of the text content of the document.

        Returns:
            int: The length of the text content of the document.
        """
        return len(self.get_text())

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the metadata of the document.

        Returns:
            Dict[str, Any]: The metadata of the document.
        """

    def get_id(self) -> int:
        """
        Get the unique identifier of the document.

        Returns:
            int: The unique identifier of the document.
        """
        return self.id

    def get_file_name(self) -> Optional[str]:
        """
        Get the filename of the document.

        Returns:
            Optional[str]: The filename of the document, or None if not applicable.
        """
        return self.file_name

    def get_file_path(self) -> Optional[str]:
        """
        Get the file path of the document.

        Returns:
            Optional[str]: The file path of the document, or None if not applicable.
        """
        return self.file_path

    def get_file_hash(self) -> str:
        """
        Get the hash of the document content.

        Returns:
            str: A hash string representing the document content.
        """
        return self.file_hash

    def get_file_type(self) -> Optional[str]:
        """
        Get the filetype of the document.

        Returns:
            Optional[str]: The filetype of the document, or None if not applicable.
        """
        return self.file_path.split(".")[-1].lower() if self.file_path else None

    def __repr__(self):
        return (
            f"BaseDocument(id={self.id}, filename='{self.get_file_name()}', "
            f"content='{self.get_text()[:50]}...', "
            f"metadata={self.get_metadata()})"
        )
