from typing import TYPE_CHECKING, List, Optional

from pydantic import field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)


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
        placeholder=400,
        description="The size of each chunk in tokens.",
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=40,
        description=(
            "The number of overlapping tokens between chunks. "
            "Must be less than chunk_size."
        ),
    )  # type: ignore

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """Validate that chunk_overlap is less than chunk_size."""
        chunk_size = info.data.get("chunk_size")
        if chunk_size is not None and v >= chunk_size:
            raise ValueError(
                f"chunk_overlap must be less than chunk_size. "
                f"Got chunk_overlap={v} and chunk_size={chunk_size}"
            )
        return v


if TYPE_CHECKING:
    from transformers import AutoTokenizer


class TokenChunkModel(BaseChunkingModel):
    SCHEMA = TokenChunkModelSchema

    def __init__(self, **kwargs):
        self.parameters = kwargs
        self.chunk_size = self.parameters["chunk_size"]
        self.chunk_overlap = self.parameters["chunk_overlap"]
        self.tokenizer_name = self.parameters["tokenizer_name"]
        self._tokenizer: Optional["AutoTokenizer"] = None
        super().__init__(**kwargs)

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)
        return self._tokenizer

    def chunk_text(self, text: str) -> List[str]:
        tokens = self.tokenizer.tokenize(text)

        token_chunks = []
        while len(tokens) > 0:
            chunk = tokens[: self.chunk_size]
            token_chunks.append(self.tokenizer.convert_tokens_to_string(chunk))
            tokens = tokens[self.chunk_size - self.chunk_overlap :]

        return token_chunks
