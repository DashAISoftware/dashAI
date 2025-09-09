from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.documents.BaseDocument import BaseDocument
from typing import List
from DashAI.back.core.schema_fields import (
    BaseSchema,
    schema_field,
    int_field,
)

class CharacterChunkModelSchema(BaseSchema):
    """Schema for character-based chunking model."""
    
    chunk_size: schema_field(
        int_field(gt=1),
        placeholder=None,
        description="Size of each chunk in characters."
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(gt=0),
        placeholder=None,
        description="Number of characters to overlap between chunks."
    )  # type: ignore
    
class CharacterChunkModel(BaseChunkingModel):
    """
    Chunking model that splits documents into chunks based on character count.
    This model is useful for processing large text documents into manageable pieces.
    """
    SCHEMA = CharacterChunkModelSchema

    def __init__(self, chunk_size: int, chunk_overlap: int):
        """
        Initialize the character chunking model with the specified chunk size and overlap.
        
        :param chunk_size: Size of each chunk in characters.
        :param chunk_overlap: Number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: BaseDocument) -> List[str]:
        """
        Split the document into chunks based on character count.
        
        :param document: The input document to be chunked.
        :return: A list of text chunks.
        """
        text = document.get_text()
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
            
        return chunks