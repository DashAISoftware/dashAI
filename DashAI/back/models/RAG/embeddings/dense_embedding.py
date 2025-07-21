from DashAI.back.models.RAG.embeddings.base_embedding import BaseEmbedding
from typing import Any, List
import numpy as np

class DenseEmbedding(BaseEmbedding):
    """
    Base class for dense embedding models.
    This class should be inherited by any specific dense embedding model implementation.
    """
    
    def __init__(self):
        super().__init__()

    def embed(self, text: str) -> List|np.ndarray|Any:
        """
        Method to generate dense embeddings for the given text.
        This method should be implemented by subclasses.
        
        :param text: The input text to embed.
        :return: A list representing the dense embeddings of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")