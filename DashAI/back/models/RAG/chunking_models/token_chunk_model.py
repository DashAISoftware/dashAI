from typing import TYPE_CHECKING, List, Optional, Tuple

from pydantic import field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)
from DashAI.back.models.RAG.exceptions import (
    RAGChunkingError,
    RAGChunkingOverlapError,
)


class TokenChunkModelSchema(BaseSchema):
    """Schema for the token-based chunking model configuration."""

    tokenizer_name: schema_field(
        enum_field(
            enum=[
                "intfloat/e5-mistral-7b-instruct",
                "dccuchile/bert-base-spanish-wwm-uncased",
            ],
        ),
        placeholder="intfloat/e5-mistral-7b-instruct",
        alias=MultilingualString(
            en="Tokenizer",
            es="Tokenizador",
            pt="Tokenizador",
            de="Tokenizer",
            zh="分词器",
        ),
        description=MultilingualString(
            en="The tokenizer model used to split the text into tokens.",
            es="El tokenizador que se usa para dividir el texto en tokens.",
            pt="O tokenizador usado para dividir o texto em tokens.",
            de="Das Tokenizer-Modell, das den Text in Tokens zerlegt.",
            zh="用于将文本切分为标记的分词器模型。",
        ),
    )  # type: ignore

    chunk_size: schema_field(
        int_field(gt=1),
        placeholder=400,
        alias=MultilingualString(
            en="Chunk size",
            es="Tamaño de fragmento",
            pt="Tamanho do fragmento",
            de="Chunk-Größe",
            zh="块大小",
        ),
        description=MultilingualString(
            en="Size of each chunk in tokens.",
            es="Tamaño de cada fragmento en tokens.",
            pt="Tamanho de cada fragmento em tokens.",
            de="Größe jedes Chunks in Tokens.",
            zh="每个块的标记数。",
        ),
    )  # type: ignore

    chunk_overlap: schema_field(
        int_field(ge=0),
        placeholder=40,
        alias=MultilingualString(
            en="Chunk overlap",
            es="Superposición entre fragmentos",
            pt="Sobreposição entre fragmentos",
            de="Chunk-Überlappung",
            zh="块重叠",
        ),
        description=MultilingualString(
            en=(
                "Number of tokens to overlap between chunks. "
                "Must be less than the chunk size."
            ),
            es=(
                "Cantidad de tokens que se repiten entre fragmentos "
                "consecutivos. Debe ser menor que el tamaño de fragmento."
            ),
            pt=(
                "Quantidade de tokens repetidos entre fragmentos consecutivos. "
                "Deve ser menor que o tamanho do fragmento."
            ),
            de=(
                "Anzahl der Tokens, die sich zwischen Chunks überlappen. "
                "Muss kleiner als die Chunk-Größe sein."
            ),
            zh="相邻块之间重叠的标记数，必须小于块大小。",
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
    """Chunking model that splits text into chunks based on token count.

    Uses a fast HuggingFace ``AutoTokenizer`` to find token boundaries and
    splits at them with configurable overlap. Each chunk is a verbatim slice
    of the source text.
    """

    SCHEMA = TokenChunkModelSchema
    CHUNK_UNIT = "tokens"
    DISPLAY_NAME = MultilingualString(
        en="Token chunking",
        es="Fragmentación por tokens",
        pt="Fragmentação por tokens",
        de="Token-basiertes Chunking",
        zh="按标记切分",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Splits documents at token boundaries using a tokenizer, so chunk "
            "sizes line up exactly with the language model's context window. "
            "Slower than character chunking and downloads a tokenizer."
        ),
        es=(
            "Divide los documentos en límites de tokens usando un tokenizador, "
            "de modo que el tamaño de los fragmentos coincide con la ventana "
            "de contexto del modelo. Es más lento que la fragmentación por "
            "caracteres y descarga un tokenizador."
        ),
        pt=(
            "Divide os documentos em limites de tokens usando um tokenizador, "
            "alinhando o tamanho dos fragmentos à janela de contexto do "
            "modelo. É mais lento que a fragmentação por caracteres e baixa "
            "um tokenizador."
        ),
        de=(
            "Teilt Dokumente an Token-Grenzen mit einem Tokenizer, sodass die "
            "Chunk-Größe exakt zum Kontextfenster des Sprachmodells passt. "
            "Langsamer als zeichenbasiertes Chunking und lädt einen Tokenizer."
        ),
        zh=(
            "使用分词器在标记边界切分文档，使块大小与语言模型的"
            "上下文窗口精确对齐。比按字符切分更慢，并且需要下载分词器。"
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the token chunking model.

        Args:
            **kwargs: Must include ``chunk_size``, ``chunk_overlap``, and
                ``tokenizer_name``.
        """
        self.chunk_size = kwargs["chunk_size"]
        self.chunk_overlap = kwargs["chunk_overlap"]
        self.tokenizer_name = kwargs["tokenizer_name"]
        self._tokenizer: Optional["AutoTokenizer"] = None
        super().__init__(**kwargs)

    @property
    def tokenizer(self) -> "AutoTokenizer":
        """Lazily load and return the HuggingFace tokenizer.

        Returns:
            AutoTokenizer: The tokenizer loaded from the configured
                ``tokenizer_name``.
        """
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer_name, use_fast=True
            )
        return self._tokenizer

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on token count.

        Each chunk is a verbatim slice of ``text``. The tokens of a window are
        used only to find the characters that window covers, never to rebuild
        the string: decoding tokens back to text loses the original casing and
        spacing, and the resulting pieces cannot be located in the source
        document, which is how :meth:`BaseChunkingModel.chunk` derives each
        chunk's pages and sources.

        Parameters
        ----------
        text : str
            The input text to be chunked.

        Returns
        -------
        list of str
            The chunks in order, each one a substring of ``text``. A window
            that holds only whitespace is skipped, as is an empty text.

        Raises
        ------
        RAGChunkingOverlapError
            If ``chunk_overlap`` is not less than ``chunk_size``.
        RAGChunkingError
            If the configured tokenizer cannot report character offsets,
            which slow tokenizers cannot.
        """
        if self.chunk_overlap >= self.chunk_size:
            raise RAGChunkingOverlapError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )
        if not text.strip():
            return []
        offsets = self._token_offsets(text)
        step = self.chunk_size - self.chunk_overlap
        chunks: List[str] = []
        for start in range(0, len(offsets), step):
            span = _window_span(offsets[start : start + self.chunk_size])
            if span is None:
                continue
            piece = text[span[0] : span[1]]
            if piece.strip():
                chunks.append(piece)
        return chunks

    def _token_offsets(self, text: str) -> List[Tuple[int, int]]:
        """Return the character span of every token of a text.

        Parameters
        ----------
        text : str
            The text to tokenize.

        Returns
        -------
        list of tuple of int
            ``(start, end)`` character offsets, one per token, in order.

        Raises
        ------
        RAGChunkingError
            If the tokenizer cannot report character offsets.
        """
        tokenizer = self.tokenizer
        if not getattr(tokenizer, "is_fast", False):
            raise self._missing_offsets_error()
        try:
            encoding = tokenizer(
                text, add_special_tokens=False, return_offsets_mapping=True
            )
            offsets = encoding["offset_mapping"]
        except (KeyError, NotImplementedError) as error:
            raise self._missing_offsets_error() from error
        return [(int(start), int(end)) for start, end in offsets]

    def _missing_offsets_error(self) -> RAGChunkingError:
        """Build the error raised when the tokenizer cannot report offsets.

        Returns
        -------
        RAGChunkingError
            An error naming the tokenizer and the requirement it misses.
        """
        return RAGChunkingError(
            f"Tokenizer '{self.tokenizer_name}' cannot report character "
            "offsets. TokenChunkModel needs an offset-capable (fast) "
            "tokenizer so every chunk stays a verbatim slice of the source "
            "text; pick a fast tokenizer or another chunking model."
        )


def _window_span(window: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Return the characters covered by a window of token offsets.

    Empty spans, which some tokenizers emit for special or added tokens, are
    ignored so they cannot widen the window.

    Parameters
    ----------
    window : list of tuple of int
        ``(start, end)`` offsets of the window's tokens, in order.

    Returns
    -------
    tuple of int, optional
        ``(first_start, last_end)`` of the non-empty spans, or ``None`` when
        the window holds none.
    """
    spans: List[Tuple[int, int]] = []
    for start, end in window:
        if end > start:
            spans.append((start, end))
    if not spans:
        return None
    return spans[0][0], spans[-1][1]
