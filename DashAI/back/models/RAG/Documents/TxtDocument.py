from .BaseDocument import BaseDocument
from typing import Dict, Any, Optional
import os

class TxtDocument(BaseDocument):
    """
    Class representing a .txt document.
    """

    def __init__(self, file_path: str):
        """
        Initialize the text document with the file path.
        
        Args:
            file_path (str): The path to the text file.
        """
        assert os.path.exists(file_path), f"File {file_path} does not exist."

        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.filetype = "txt"
        self.text_length = len(self.text)
        self.metadata = {
            "file_path": file_path,
            "filetype": self.filetype,
            "filename": self.filename,
        }
        self.text_length = len(self.get_text())

    def get_text(self) -> str:
        """
        Get the text content of the document.
        
        Returns:
            str: The text content of the document.
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return text.strip()
    
    def get_text_length(self) -> int:
        return self.text_length
    
    def get_metadata(self) -> Dict[str, Any]:
        return self.metadata
    
    def get_filename(self) -> str:
        return self.filename
    
    def get_filetype(self) -> str:
        return self.filetype
    
    def get_file_location(self) -> str:
        return self.file_path