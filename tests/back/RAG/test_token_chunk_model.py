"""TokenChunkModel returns verbatim slices of the source text.

``BaseChunkingModel.chunk`` locates every chunk in the joined document text to
derive its pages and sources, so a token chunker that reconstructs text from
tokens loses both the original casing and the page provenance. These tests pin
chunks to substrings of the input and cover the sliding window that produces
them: its count, its overlap, its contiguity and the whitespace-only windows it
drops.
"""

import math
import re
from typing import List, Optional, Tuple

import pytest

from DashAI.back.dataloaders.classes.dashai_document import (
    DashAIDocument,
    DocumentItem,
)
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    SEPARATOR,
)
from DashAI.back.models.RAG.chunking_models.token_chunk_model import (
    TokenChunkModel,
    _window_span,
)
from DashAI.back.models.RAG.exceptions import RAGChunkingError
from DashAI.back.types.value_types import Text

PAGE_ONE = "La Nube Blanca subió al Cielo en 2024 y trajo Lluvia Fina."
PAGE_TWO = "Segunda Línea: ¿Qué Tal? Otra Vez la Nube Bajó con Viento Fuerte."
TOKENIZER_NAME = "dccuchile/bert-base-spanish-wwm-uncased"


class _LossyOffsetTokenizer:
    """A fast-tokenizer stand-in whose decode path loses casing.

    ``__call__`` reports the character span of every whitespace-separated
    word, like a fast tokenizer's ``offset_mapping``. ``tokenize`` and
    ``convert_tokens_to_string`` reproduce the old lossy path but succeed: a
    chunker that still rebuilds the text from tokens returns lowercased,
    space-joined pieces instead of raising, so the assertions on the chunks
    themselves are what catch the regression. ``decode_calls`` counts how
    often the lossy path was taken.
    """

    is_fast = True

    def __init__(self):
        self.decode_calls = 0

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        assert add_special_tokens is False
        assert return_offsets_mapping is True
        return {
            "offset_mapping": [
                (match.start(), match.end()) for match in re.finditer(r"\S+", text)
            ]
        }

    def tokenize(self, text):
        return [token.lower() for token in text.split()]

    def convert_tokens_to_string(self, tokens):
        self.decode_calls += 1
        return " ".join(token.lower() for token in tokens)


class _ScriptedOffsetTokenizer:
    """A fast-tokenizer stand-in that reports caller-supplied offsets.

    The offsets are independent of the text so a test can place the window
    boundaries exactly.
    """

    is_fast = True

    def __init__(self, offsets: List[Tuple[int, int]]):
        self.offsets = offsets

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        assert add_special_tokens is False
        assert return_offsets_mapping is True
        return {"offset_mapping": list(self.offsets)}


class _FailingOffsetTokenizer:
    """A fast tokenizer whose offset request fails with a given error."""

    is_fast = True

    def __init__(self, error: Exception):
        self.error = error

    def __call__(self, *args, **kwargs):
        raise self.error


def _document() -> DashAIDocument:
    return DashAIDocument.from_items(
        [
            DocumentItem(Text, PAGE_ONE, page=1),
            DocumentItem(Text, PAGE_TWO, page=2),
        ],
        metadata={"file_name": "two.pdf"},
    )


def _joined_text() -> str:
    return SEPARATOR.join([PAGE_ONE, PAGE_TWO])


def _model(
    chunk_size: int,
    chunk_overlap: int,
    tokenizer: Optional[object] = None,
) -> TokenChunkModel:
    model = TokenChunkModel(
        tokenizer_name=TOKENIZER_NAME,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if tokenizer is not None:
        model._tokenizer = tokenizer
    return model


def _chunk_spans(chunks: List[str], text: str) -> List[Tuple[int, int]]:
    """Return the ``(start, end)`` span of every chunk, in chunk order."""
    spans: List[Tuple[int, int]] = []
    cursor = 0
    for chunk in chunks:
        start = text.find(chunk, cursor)
        assert start >= 0, f"chunk {chunk!r} is not a substring of the text"
        spans.append((start, start + len(chunk)))
        cursor = start + 1
    return spans


def test_chunks_are_verbatim_slices_of_the_source_text():
    model = _model(8, 2, _LossyOffsetTokenizer())

    chunks = model.chunk_text(_joined_text())

    assert len(chunks) > 1
    assert all(chunk in _joined_text() for chunk in chunks)


def test_chunks_keep_the_original_casing():
    model = _model(8, 2, _LossyOffsetTokenizer())

    chunks = model.chunk_text(_joined_text())

    assert any(character.isupper() for chunk in chunks for character in chunk)
    assert chunks[0].startswith("La Nube")


def test_the_lossy_decode_path_is_never_used():
    stub = _LossyOffsetTokenizer()
    model = _model(8, 2, stub)

    model.chunk_text(_joined_text())

    assert stub.decode_calls == 0


@pytest.mark.parametrize(
    ("n_tokens", "chunk_size", "chunk_overlap"),
    [(15, 8, 2), (10, 4, 1), (9, 4, 0), (5, 6, 1)],
)
def test_window_count_follows_the_token_step(n_tokens, chunk_size, chunk_overlap):
    text = " ".join([f"palabra{index}" for index in range(n_tokens)])
    model = _model(chunk_size, chunk_overlap, _LossyOffsetTokenizer())

    chunks = model.chunk_text(text)

    step = chunk_size - chunk_overlap
    assert len(chunks) == math.ceil(n_tokens / step)


def test_consecutive_windows_overlap():
    text = "0123"
    offsets = [(index, index + 1) for index in range(len(text))]
    model = _model(4, 2, _ScriptedOffsetTokenizer(offsets))

    chunks = model.chunk_text(text)

    assert chunks == ["0123", "23"]
    spans = _chunk_spans(chunks, text)
    assert spans[1][0] < spans[0][1]


def test_consecutive_windows_leave_no_gap():
    text = "0123456789"
    offsets = [(index, index + 1) for index in range(len(text))]
    model = _model(4, 0, _ScriptedOffsetTokenizer(offsets))

    chunks = model.chunk_text(text)

    assert chunks == ["0123", "4567", "89"]
    spans = _chunk_spans(chunks, text)
    for index in range(len(spans) - 1):
        assert spans[index + 1][0] <= spans[index][1]
    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)


@pytest.mark.parametrize(
    ("window", "expected"),
    [
        ([], None),
        ([(3, 3), (7, 7)], None),
        ([(4, 9)], (4, 9)),
        ([(0, 0), (2, 5), (5, 5), (7, 9), (9, 9)], (2, 9)),
    ],
)
def test_window_span_ignores_empty_token_spans(window, expected):
    assert _window_span(window) == expected


def test_a_whitespace_only_trailing_window_is_dropped():
    text = "alpha beta\n\n\n\n"
    offsets = [(0, 5), (6, 10), (10, 14)]
    model = _model(2, 0, _ScriptedOffsetTokenizer(offsets))

    chunks = model.chunk_text(text)

    assert chunks == ["alpha beta"]


def test_empty_text_gives_no_chunks():
    model = _model(8, 2, _LossyOffsetTokenizer())

    assert model.chunk_text("") == []
    assert model.chunk_text("   \n\t ") == []


def test_a_slow_tokenizer_is_rejected_instead_of_decoding_tokens():
    class _SlowTokenizer:
        is_fast = False

        def __call__(self, *args, **kwargs):
            raise AssertionError("a slow tokenizer must be rejected up front")

    model = _model(8, 2, _SlowTokenizer())

    with pytest.raises(RAGChunkingError, match=TOKENIZER_NAME):
        model.chunk_text(_joined_text())


@pytest.mark.parametrize(
    "error",
    [NotImplementedError("no offset mapping"), KeyError("offset_mapping")],
)
def test_tokenizer_offset_failures_become_chunking_errors(error):
    model = _model(8, 2, _FailingOffsetTokenizer(error))

    with pytest.raises(RAGChunkingError, match=TOKENIZER_NAME):
        model.chunk_text(_joined_text())


def test_unrelated_tokenizer_failures_propagate():
    model = _model(8, 2, _FailingOffsetTokenizer(ValueError("boom")))

    with pytest.raises(ValueError, match="boom"):
        model.chunk_text(_joined_text())


def test_real_tokenizer_keeps_text_and_pages():
    from transformers import AutoTokenizer

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            TOKENIZER_NAME, use_fast=True, local_files_only=True
        )
    except OSError as error:
        pytest.skip(f"tokenizer {TOKENIZER_NAME} is not cached offline: {error}")

    model = _model(12, 3, tokenizer)

    chunked = model.chunk(_document())
    chunks = [item.content for item in chunked.items()]

    assert len(chunks) > 1
    assert all(chunk in _joined_text() for chunk in chunks)
    assert any(character.isupper() for chunk in chunks for character in chunk)
    pages = {item.page for item in chunked.items()}
    assert pages == {1, 2}
