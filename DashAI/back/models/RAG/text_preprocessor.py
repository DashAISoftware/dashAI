import re
from typing import Dict

class TextPreprocessor:
    """
    A simple text preprocessor that removes special characters and extra spaces from text.
    This is useful for cleaning text data before processing.
    """

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess the text by removing special characters and extra spaces.
        Args:
            text (str): The text to be preprocessed.
        Returns:
            str: The preprocessed text.
        """
        # Remove special characters except for periods, commas, and spaces
        pattern = r"[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ(),¿?¡! \[\]:;\n\-_]+"
        text = re.sub(pattern, " ", text).strip()
        # Remove extra spaces
        text = re.sub(r"\s+", " ", text)
        return text
    
    @staticmethod
    def preprocess_documents_texts(documents: Dict[str, str]) -> Dict[str, str]:
        """
        Preprocess the documents' texts.
        Args:
            documents (Dict[str, str]): A dictionary of documents with filenames as keys and content as values.
        Returns:
            Dict[str, str]: A dictionary of preprocessed documents with filenames as keys and preprocessed content as values.
        """
        preprocessed_documents = {}
        for filename, content in documents.items():
            preprocessed_content = TextPreprocessor.preprocess_text(content)
            preprocessed_documents[filename] = preprocessed_content
        return preprocessed_documents