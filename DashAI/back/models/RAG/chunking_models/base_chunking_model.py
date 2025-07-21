from abc import ABCMeta, abstractmethod
from DashAI.back.config_object import ConfigObject
from DashAI.back.models.RAG.documents.BaseDocument import BaseDocument
from typing import Final, List

class BaseChunkingModel(ConfigObject, metaclass=ABCMeta):
    """
    Base class for chunking models.
    This class should be inherited by any specific chunking model implementation.
    """
    
    TYPE: Final[str] = "ChunkingModel"

    def __init__(self, **kwargs):
        """
        Initialize the chunking model with any necessary parameters.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")

    @abstractmethod
    def chunk(self, document: BaseDocument, **kwargs) -> List[str]:
        """
        Method to be implemented by subclasses to perform document chunking.

        :param document: The input document to be chunked.
        :return: A list of text chunks.
        """
        raise NotImplementedError("Subclasses must implement this method.")