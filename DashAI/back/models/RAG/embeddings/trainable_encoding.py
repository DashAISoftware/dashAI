from abc import ABCMeta
import hashlib
from typing import Any, List
import numpy as np

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.embeddings.dense_embedding import DenseEmbedding

class TrainableEncoding(DenseEmbedding):
    """
    Base class for all encoding (embedding) models.
    This class should be inherited by any specific encoding (embedding) model implementation.
    """
    EMBEDDINGS_PATH = "RAG/embeddings"
    
    def __init__(
            self, 
            **kwargs: Any):
        """
        Initialize the encoding (embedding) model with the given documents.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")
    
    def _get_encoding_signature(self) -> str:
        """
        Generate a hash to identify the encoding (embedding) for caching purposes.

        Hash is calculated over the documents' content to ensure consistency in encodings, it must:
        - Be consistent across runs with the same documents content, chunking strategy and encoding model parameters.
        - Change if the documents are modified.
        - Change if the documents content is modified.
        - Change if the chunking strategy is modified.
        - Change if the encoding model parameters are modified.

        Returns:
            str: A hash string representing the encodings (embeddings).
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    def _calculate_documents_chunks_hash(self) -> str:
        """
        Generate a hash to identify the documents chunks' texts for caching purposes.

        Hash is calculated over the chunks' texts to ensure consistency in encodings, it must:
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

    def encode(self, text: str) -> List[float]|np.ndarray|Any:
        """
        Method to generate encodings (embeddings) for the given text.
        This method should be implemented by subclasses.

        :param text: The input text to encode (embed).
        :return: A list representing the encodings (embeddings) of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")