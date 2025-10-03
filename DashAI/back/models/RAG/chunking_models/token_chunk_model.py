from transformers import AutoTokenizer

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.models.RAG.chunking_models.base_chunking_model import BaseChunkingModel
from DashAI.back.models.RAG.documents import BaseDocument


class TokenChunkModelSchema(BaseSchema):
    tokenizer_name: schema_field(
        enum_field(
            enum=[
                "intfloat/e5-mistral-7b-instruct",
                "dccuchile/bert-base-spanish-wwm-uncased",
            ],
        ),
        placeholder="intfloat/e5-mistral-7b-instruct",
        description="The tokenizer model to use for tokenizing the text.",
    )  # type: ignore

    chunk_size: schema_field(
        int_field(gt=1),
        placeholder=200,
        description="The size of each chunk in tokens.",
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=20,
        description="The number of overlapping tokens between chunks.",
    )  # type: ignore


class TokenChunkModel(BaseChunkingModel):
    SCHEMA = TokenChunkModelSchema

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)

        self.chunk_size = kwargs.get("chunk_size", 200)
        self.chunk_overlap = kwargs.get("chunk_overlap", 20)

        self.tokenizer_name = kwargs.get(
            "tokenizer_name", "intfloat/e5-mistral-7b-instruct"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)

    def chunk(self, document: BaseDocument):
        text = document.get_text()

        tokens = self.tokenizer.tokenize(text)

        chunks = []
        for i in range(0, len(tokens), self.chunk_size):
            chunk = tokens[i : i + self.chunk_size]
            chunks.append(chunk)

        return chunks
