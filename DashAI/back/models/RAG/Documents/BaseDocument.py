from abc import ABC
import hashlib
from typing import Any, Dict, List, Optional

class BaseDocument(ABC):
    """
    Base class for documents.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the document.
        """
        pass

    def get_text(self) -> str:  
        """
        Get the text content of the document.
        
        Returns:
            str: The text content of the document.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_text_length(self) -> int:
        """
        Get the length of the text content of the document.
        
        Returns:
            int: The length of the text content of the document.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the metadata of the document.
        
        Returns:
            Dict[str, Any]: The metadata of the document.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_filename(self) -> Optional[str]:
        """
        Get the filename of the document.
        
        Returns:
            Optional[str]: The filename of the document, or None if not applicable.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_filetype(self) -> Optional[str]:
        """
        Get the filetype of the document.
        
        Returns:
            Optional[str]: The filetype of the document, or None if not applicable.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_file_location(self) -> Optional[str]:
        """
        Get the file location of the document.
        
        Returns:
            Optional[str]: The file location of the document, or None if not applicable.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def get_chunks(self, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Get the document text split into chunks.
        
        Args:
            chunk_size (int): The size of each chunk.
            chunk_overlap (int): The overlap between chunks.
        
        Returns:
            List[str]: A list of text chunks.
        """
        text = self.get_text()
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - chunk_overlap
        return chunks
    
    def get_hash(self) -> str:
        """
        Get a hash of the document content.
        
        Returns:
            str: A hash string representing the document content.
        """
        text = self.get_text()
        return hashlib.sha256(text.encode('utf-8')).hexdigest() if text else ''
    
    def __repr__(self):
        return f"BaseDocument(filename='{self.get_filename()}', content='{self.get_text()[:50]}...', metadata={self.get_metadata()})"

