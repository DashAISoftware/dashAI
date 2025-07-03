from .BaseDocument import BaseDocument
import os
from PyPDF2 import PdfReader
import base64

class PDFDocument(BaseDocument):
    """
    Class representing a PDF document.
    """

    def __init__(self, file_path: str):
        """
        Initialize the PDF document with the file path.
        
        Args:
            file_path (str): The path to the PDF file.
        """
        
        assert os.path.exists(file_path), f"File {file_path} does not exist."

        self.file_path = file_path
        self.metadata = {
            "file_path": file_path,
            "filetype": "pdf",
            "filename": os.path.basename(file_path),
        }
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.filetype = "pdf"        
        self.text_length = len(self.get_text())

    def get_text(self) -> str:
        reader = PdfReader(self.file_path)
        if not reader.pages:
            raise ValueError(f"The PDF file {self.file_path} is empty or not valid.")

        # Extract text from all pages
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        return text.strip()
    
    def get_text_length(self) -> int:
        return self.text_length
    
    def get_metadata(self) -> dict:
        return self.metadata
    
    def get_filename(self) -> str:
        return self.filename
    
    def get_filetype(self) -> str:
        return self.filetype
    
    def get_file_location(self) -> str:
        return self.file_path
    