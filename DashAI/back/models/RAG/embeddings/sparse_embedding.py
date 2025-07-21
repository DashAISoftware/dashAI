import numpy as np
from DashAI.back.models.RAG.documents import BaseDocument
from DashAI.back.models.RAG.embeddings.base_embedding import BaseEmbedding
from typing import Any, List

class SparseEmbedding(BaseEmbedding):
    """
    Base class for sparse embedding models.
    This class should be inherited by any specific sparse embedding model implementation.
    """
    
    def __init__(self, documents: List[BaseDocument], **kwargs: Any):
        """
        Initialize the sparse embedding model with the given documents.
        
        :param documents: List of documents to be embedded.
        :param kwargs: Additional keyword arguments.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")

    def embed(self, text: str) -> List|np.ndarray|Any:
        """
        Method to generate sparse embeddings for the given text.
        This method should be implemented by subclasses.
        
        :param text: The input text to embed.
        :return: A list representing the sparse embeddings of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")