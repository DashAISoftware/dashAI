import numpy as np
from DashAI.back.models.RAG.documents import BaseDocument
from DashAI.back.models.RAG.encodings.encoding import Encoding
from typing import Any, List

class SparseEncoding(Encoding):
    """
    Base class for sparse encoding (embedding) models.
    This class should be inherited by any specific sparse encoding (embedding) model implementation.
    """
    
    def __init__(self, documents: List[BaseDocument], **kwargs: Any):
        """
        Initialize the sparse encoding (embedding) model with the given documents.
        
        :param documents: List of documents to be embedded.
        :param kwargs: Additional keyword arguments.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")

    def encode(self, text: str) -> List|np.ndarray|Any:
        """
        Method to generate sparse encodings (embeddings) for the given text.
        This method should be implemented by subclasses.
        
        :param text: The input text to embed.
        :return: A list representing the sparse encodings (embeddings) of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")