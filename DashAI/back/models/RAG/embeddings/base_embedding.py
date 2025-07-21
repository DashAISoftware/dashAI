from abc import ABCMeta
import hashlib
from DashAI.back.config_object import ConfigObject
from typing import Any, List
import numpy as np

from DashAI.back.models.RAG.documents.BaseDocument import BaseDocument

class BaseEmbedding(ConfigObject, metaclass=ABCMeta):
    """
    Base class for all embedding models.
    This class should be inherited by any specific embedding model implementation.
    """
    EMBEDDINGS_PATH = "RAG/embeddings"
    
    def __init__(
            self, 
            documents: List[BaseDocument], 
            **kwargs: Any):
        """
        Initialize the embedding model with the given documents.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")
    
    def _calculate_embeddings_hash(self) -> str:
        """
        Generate a hash to identify the embeddings for caching purposes.
        
        Hash is calculated over the documents' content to ensure consistency in embeddings, it must:
        - Be consistent across runs with the same documents content, chunking strategy and embedding model parameters.
        - Change if the documents are modified.
        - Change if the documents content is modified.
        - Change if the chunking strategy is modified.
        - Change if the embedding model parameters are modified.
        
        Returns:
            str: A hash string representing the embeddings.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    def _calculate_documents_chunks_hash(self) -> str:
        """
        Generate a hash to identify the documents chunks' texts for caching purposes.

        Hash is calculated over the chunks' texts to ensure consistency in embeddings, it must:
        - Be consistent across runs with the same documents content and chunking strategy.
        - Change if the documents are modified.
        - Change if the documents content is modified.
        - Change if the chunking strategy is modified.

        Returns:
            str: A hash string representing the documents chunks.
        """
        joint_text = ""
        self.documents_chunks = sorted(self.documents_chunks.items())
        for doc_id in self.documents_chunks.keys():
            for i, chunk in enumerate(self.documents_chunks[doc_id]):
                joint_text += f"{doc_id}_{i}:{chunk}\n"
            
        return hashlib.sha256(joint_text.encode('utf-8')).hexdigest()

    def embed(self, text: str) -> List[float]|np.ndarray|Any:
        """
        Method to generate embeddings for the given text.
        This method should be implemented by subclasses.
        
        :param text: The input text to embed.
        :return: A list representing the embeddings of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")