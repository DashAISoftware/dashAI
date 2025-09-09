
from DashAI.back.models.RAG.encodings.encoding import Encoding


class DenseEncoding(Encoding):
    """
    Base class for all dense encoding (embedding) models.
    """

    def __init__(self, **kwargs):
        """
        Initialize the dense encoding (embedding) model with the given documents.
        """
        raise NotImplementedError("Subclasses must implement the __init__ method.")

    def encode(self, text: str):
        """
        Method to generate dense encodings (embeddings) for the given text.
        This method should be implemented by subclasses.

        :param text: The input text to encode (embed).
        :return: A list representing the dense encodings (embeddings) of the input text.
        """
        raise NotImplementedError("Subclasses must implement this method.")