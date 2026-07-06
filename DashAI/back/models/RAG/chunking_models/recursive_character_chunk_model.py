from typing import List

from pydantic import field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
    list_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)


class RecursiveCharacterChunkModelSchema(BaseSchema):
    chunk_size: schema_field(
        int_field(gt=1),
        placeholder=1000,
        description=MultilingualString(
            en="Size of each chunk in characters.",
            es="Tamaño de cada fragmento en caracteres.",
        ),
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=100,
        description=MultilingualString(
            en=(
                "Number of characters to overlap between chunks. "
                "Must be less than chunk_size."
            ),
            es=(
                "Número de caracteres a solapar entre fragmentos. "
                "Debe ser menor que chunk_size."
            ),
        ),
    )  # type: ignore

    separators: schema_field(
        list_field(string_field(), min_items=1),
        placeholder=["\n\n", "\n", ".", " ", ""],
        description=MultilingualString(
            en="Ordered list of separators to use for splitting.",
            es="Lista ordenada de separadores a usar para dividir.",
        ),
    )  # type: ignore

    @field_validator("chunk_overlap", mode="after")
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        chunk_size = info.data.get("chunk_size")
        if chunk_size is not None and v >= chunk_size:
            raise ValueError(
                f"chunk_overlap must be less than chunk_size. "
                f"Got chunk_overlap={v} and chunk_size={chunk_size}"
            )
        return v


class RecursiveCharacterChunkModel(BaseChunkingModel):
    SCHEMA = RecursiveCharacterChunkModelSchema

    DISPLAY_NAME: str = MultilingualString(
        en="Recursive Character Chunk Model",
        es="Modelo de Fragmentación Recursiva por Caracteres",
    )

    FLAGS: list[str] = []

    def __init__(self, **kwargs):
        self.chunk_size = kwargs["chunk_size"]
        self.chunk_overlap = kwargs["chunk_overlap"]
        self.separators = kwargs["separators"]
        super().__init__(**kwargs)

    def chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        return self._split_text(text, 0)

    def _split_text(self, text: str, separator_idx: int) -> List[str]:
        if separator_idx >= len(self.separators):
            return self._force_split(text)

        separator = self.separators[separator_idx]

        if separator == "" or separator not in text:
            return self._split_text(text, separator_idx + 1)

        splits = text.split(separator)
        return self._recursive_split(splits, separator_idx + 1)

    def _recursive_split(self, splits: List[str], next_sep_idx: int) -> List[str]:
        result: List[str] = []
        for split in splits:
            if len(split) <= self.chunk_size:
                result.append(split)
                continue

            resolved = False
            for sep_idx in range(next_sep_idx, len(self.separators)):
                separator = self.separators[sep_idx]
                if separator == "" or separator in split:
                    result.extend(self._split_text(split, sep_idx))
                    resolved = True
                    break

            if not resolved:
                result.extend(self._force_split(split))

        return result

    def _force_split(self, text: str) -> List[str]:
        chunks: List[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunks.append(text[start:end])
            if end == text_length:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks
