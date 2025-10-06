from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field
    )
from transformers import AutoTokenizer

from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.documents import BaseDocument

class TokenChunkModelSchema(BaseSchema):
    tokenizer_name: enum_field(
        enum=[
            "intfloat/e5-mistral-7b-instruct",
            "dccuchile/bert-base-spanish-wwm-uncased"
        ]
    ) #type: ignore

    chunk_size: int_field(
        gt=1,
    ) #type: ignore

    chunk_overlap: int_field(
        ge=0,
    ) #type: ignore

class TokenChunkModel(BaseChunkingModel):

    SCHEMA = TokenChunkModelSchema

    def __init__(self, **kwargs):
        
        kwargs = self.validate_and_transform(kwargs)

        self.chunk_size = kwargs.get("chunk_size")
        self.chunk_overlap = kwargs.get("chunk_overlap")

        self.tokenizer_name = kwargs.get("tokenizer_name")
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)


    def chunk_document(self, document:BaseDocument):
        text = document.get_text()

        tokens = self.tokenizer.tokenize(text)

        chunks = []
        for i in range(0, len(tokens), self.chunk_size):
            chunk = tokens[i:i + self.chunk_size]
            chunks.append(chunk)

        return chunks