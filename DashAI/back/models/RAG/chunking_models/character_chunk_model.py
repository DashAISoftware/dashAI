from typing import List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
    schema_field,
)
from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk


class CharacterChunkModelSchema(BaseSchema):
    """Schema for character-based chunking model."""

    chunk_size: schema_field(
        int_field(gt=1),
        placeholder=200,
        description="Size of each chunk in characters.",
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(gt=0),
        placeholder=20,
        description="Number of characters to overlap between chunks.",
    )  # type: ignore


class CharacterChunkModel(BaseChunkingModel):
    """
    Chunking model that splits documents into chunks based on character count.
    This model is useful for processing large text documents into manageable pieces.
    """

    SCHEMA = CharacterChunkModelSchema

    def __init__(self, **kwargs):
        """
        Initialize the character chunking model with the specified chunk size and
        overlap.

        Args:
            chunk_size (int): Size of each chunk in characters.
            chunk_overlap (int): Number of characters to overlap between chunks.
        """
        self.chunk_size = kwargs["chunk_size"]
        self.chunk_overlap = kwargs["chunk_overlap"]
        super().__init__(**kwargs)

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk the input text into smaller segments based on character count.

        Args:
            text (str): The input text to be chunked.
        
        Returns:
            List[str]: A list of text chunks.
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            if end == text_length:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks