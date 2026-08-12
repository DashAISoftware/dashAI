"""PDF text extractor using the textract library."""

import re
from typing import ClassVar, Final, List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    schema_field,
    string_field,
)
from DashAI.back.models.RAG.exceptions import RAGDocumentParsingError
from DashAI.back.models.RAG.extractors.base_extractor import BaseExtractor


def _clean_textract_output(text: str) -> str:
    """Clean textract output."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class TextractSchema(BaseSchema):
    """Schema for TextractExtractor parameters."""

    language: schema_field(
        string_field(),
        placeholder="",
        description="Language code for OCR (e.g. 'eng', 'spa'). Empty = auto-detect.",
    )  # type: ignore[valid-type]
    method: schema_field(
        string_field(),
        placeholder="",
        description=(
            "Force a specific extraction backend "
            "(e.g. 'pdfminer', 'tesseract'). Empty = auto-detect."
        ),
    )  # type: ignore[valid-type]


class TextractExtractor(BaseExtractor):
    """PDF text extractor using the textract library.

    Requires system-level tools (e.g. pdftotext, tesseract-ocr).
    """

    TYPE: Final[str] = "Extractor"
    SCHEMA: ClassVar[BaseSchema] = TextractSchema
    SUPPORTED_FILE_TYPES: List[str] = ["pdf"]

    def __init__(self, **kwargs):
        self.language = kwargs.get("language") or None
        self.method = kwargs.get("method") or None
        super().__init__(**kwargs)

    def extract(self, file_path: str) -> str:
        import textract

        kwargs: dict = {"output_encoding": "utf-8"}
        if self.language:
            kwargs["language"] = self.language
        if self.method:
            kwargs["method"] = self.method

        try:
            text = textract.process(file_path, **kwargs).decode("utf-8")
            return _clean_textract_output(text)
        except Exception as e:
            raise RAGDocumentParsingError(
                f"Textract failed to extract text from {file_path}: {e}"
            ) from e
