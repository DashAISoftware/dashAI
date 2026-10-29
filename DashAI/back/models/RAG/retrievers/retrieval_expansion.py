"""Shared retrieve-then-expand options for every retriever schema.

Retrieval returns isolated chunks, so an answer that spans a chunk boundary
loses part of its context. Retrieve-then-expand keeps the retrieval (and, in a
composite, the re-ranking) untouched and widens only the retriever's **final**
output: each retrieved chunk is replaced by a window of
``expand_window`` consecutive chunks around it, and overlapping windows are
merged into one concatenated unit.

The options live in this module instead of in each retriever so the semantics,
the defaults and the user-facing labels stay identical across all retrievers.
"""

from typing import Any, Dict, Final, Tuple

from pydantic import field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents.chunk import Chunk

#: Schema param name of the retrieve-then-expand switch.
ENABLE_FIELD: Final[str] = "enable_retrieve_then_expand"

#: Schema param name of the expansion window size.
WINDOW_FIELD: Final[str] = "expand_window"

#: Whether retrievers expand their final output by default.
DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND: Final[bool] = False

#: Total number of chunks in an expanded window (including the retrieved one).
DEFAULT_EXPAND_WINDOW: Final[int] = 3

#: Largest accepted expansion window. It bounds how much prompt context a
#: window may add, which the session's context budget multiplies out.
MAX_EXPAND_WINDOW: Final[int] = 32

#: Separator placed between the texts of the chunks merged into one unit.
EXPANDED_CHUNK_SEPARATOR: Final[str] = " "


def _strip_expansion_value(value: Any) -> Any:
    """Copy a parameters value, dropping the expansion options at every level.

    Parameters
    ----------
    value : Any
        Parameters value: a mapping, a list or a leaf.

    Returns
    -------
    Any
        A deep-enough copy without ``enable_retrieve_then_expand`` or
        ``expand_window`` anywhere inside it.
    """
    if isinstance(value, dict):
        return strip_expansion_options(value)
    if isinstance(value, list):
        stripped_list: list = []
        for item in value:
            stripped_list.append(_strip_expansion_value(item))
        return stripped_list
    return value


def strip_expansion_options(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *params* without the retrieve-then-expand options.

    The two options are post-processing knobs: they never change what is
    indexed nor which stored model a configuration resolves to. They must
    therefore be excluded wherever a configuration acts as an *identity* — the
    sparse persistence hash, the retriever table's natural key, the preset
    match and the cleanup decision — or toggling them would force a re-index.
    Removal is recursive so a composite's children are stripped too.

    Parameters
    ----------
    params : Dict[str, Any]
        Retriever parameters, possibly holding nested ``children`` refs.

    Returns
    -------
    Dict[str, Any]
        A copy with ``ENABLE_FIELD`` and ``WINDOW_FIELD`` removed at every
        level. The input mapping is never mutated.
    """
    stripped: Dict[str, Any] = {}
    for key, value in params.items():
        if key in (ENABLE_FIELD, WINDOW_FIELD):
            continue
        stripped[key] = _strip_expansion_value(value)
    return stripped


def expansion_span(chunk: Chunk) -> int:
    """Return how many document positions *chunk* covers.

    Parameters
    ----------
    chunk : Chunk
        Retrieved chunk, possibly expanded.

    Returns
    -------
    int
        The number of covered positions, or ``1`` for a stored chunk.
    """
    covered: Tuple[int, ...] | None = getattr(chunk, "source_positions", None)
    if not covered:
        return 1
    return max(covered) - min(covered) + 1


def prefer_wider_chunk(current: Chunk, candidate: Chunk) -> Chunk:
    """Return the chunk covering more document positions.

    Two chunks sharing ``(document_id, document_position)`` are the same
    retrieval slot seen twice. When one of them is an expanded unit it covers
    more than that anchor position, so keeping the wider one preserves the
    context the narrower one would drop. A tie keeps the first chunk, which
    preserves the existing first-wins ordering.

    Parameters
    ----------
    current : Chunk
        Chunk already placed in the merged result.
    candidate : Chunk
        Later chunk with the same ``(document_id, document_position)`` key.

    Returns
    -------
    Chunk
        *current* when it covers at least as many positions as *candidate*,
        otherwise *candidate*.
    """
    if expansion_span(candidate) > expansion_span(current):
        return candidate
    return current


class RetrievalExpansionSchema(BaseSchema):
    """Schema mixin adding the shared retrieve-then-expand options.

    Attributes:
        enable_retrieve_then_expand: Whether the retriever widens its final
            output with context chunks. Disabled by default, so every existing
            configuration keeps its current behaviour.
        expand_window: Total number of chunks in an expanded window, including
            the retrieved one. Odd values are centred exactly on the retrieved
            chunk; even values keep the extra chunk after it. Windows are
            clamped to the document bounds, and overlapping windows are merged
            into a single unit. Bounded by ``[1, MAX_EXPAND_WINDOW]`` so one
            window cannot inflate the prompt without limit.
    """

    enable_retrieve_then_expand: schema_field(
        bool_field(),
        placeholder=DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND,
        description=MultilingualString(
            en="Widen each retrieved chunk with its neighbouring chunks before"
            " the chunks are returned as the retriever's context.",
            es="Ampliar cada fragmento recuperado con sus fragmentos vecinos"
            " antes de devolverlos como contexto del recuperador.",
            pt="Ampliar cada trecho recuperado com seus trechos vizinhos antes"
            " de devolvê-los como contexto do recuperador.",
            de="Jedes abgerufene Fragment vor der Rückgabe als Kontext des"
            " Retrievers um seine benachbarten Fragmente erweitern.",
            zh="在将片段作为检索器上下文返回之前，用相邻片段扩展每个已检索片段。",
        ),
        alias=MultilingualString(
            en="Retrieve then expand",
            es="Recuperar y expandir",
            pt="Recuperar e expandir",
            de="Abrufen und erweitern",
            zh="检索后扩展",
        ),
    ) = DEFAULT_ENABLE_RETRIEVE_THEN_EXPAND  # type: ignore

    expand_window: schema_field(
        int_field(ge=1, le=MAX_EXPAND_WINDOW),
        placeholder=DEFAULT_EXPAND_WINDOW,
        description=MultilingualString(
            en="Total number of chunks in the expanded window, the retrieved"
            " one included. Odd values are centred exactly on the retrieved"
            " chunk; even values keep the extra chunk after it. Windows never"
            " leave the document, and overlapping windows merge into one"
            " concatenated chunk.",
            es="Número total de fragmentos de la ventana expandida, incluido el"
            " recuperado. Los valores impares se centran exactamente en el"
            " fragmento recuperado; los pares dejan el fragmento extra después"
            " de él. La ventana nunca sale del documento y las ventanas"
            " superpuestas se fusionan en un solo fragmento concatenado.",
            pt="Número total de trechos na janela expandida, incluindo o"
            " recuperado. Valores ímpares são centrados exatamente no trecho"
            " recuperado; valores pares deixam o trecho extra depois dele. A"
            " janela nunca sai do documento e janelas sobrepostas são fundidas"
            " em um único trecho concatenado.",
            de="Gesamtzahl der Fragmente im erweiterten Fenster, einschließlich"
            " des abgerufenen. Ungerade Werte werden exakt auf das abgerufene"
            " Fragment zentriert; gerade Werte behalten das zusätzliche Fragment"
            " danach. Fenster verlassen das Dokument nie, und überlappende"
            " Fenster werden zu einem verketteten Fragment zusammengeführt.",
            zh="扩展窗口中的片段总数（包含已检索片段）。奇数值完全以已检索片段为中心；"
            "偶数值将额外的片段放在其之后。窗口不会超出文档边界，重叠的窗口会合并为"
            "单个拼接片段。",
        ),
        alias=MultilingualString(
            en="Expansion window",
            es="Ventana de expansión",
            pt="Janela de expansão",
            de="Erweiterungsfenster",
            zh="扩展窗口",
        ),
    ) = DEFAULT_EXPAND_WINDOW  # type: ignore

    @field_validator(ENABLE_FIELD, mode="before")
    @classmethod
    def _reject_non_boolean_flag(cls, value: Any) -> Any:
        """Reject a non-boolean switch instead of coercing it.

        Pydantic would accept ``"false"``, ``0`` or ``None`` and silently turn
        the feature off; the retriever constructor rejects those values, so the
        schema has to reject them too or a stored configuration would validate
        and then fail at construction.

        Parameters
        ----------
        value : Any
            Raw field value.

        Returns
        -------
        Any
            The unchanged value when it is a real ``bool``.

        Raises
        ------
        ValueError
            If the value is not a real ``bool``.
        """
        if not isinstance(value, bool):
            raise ValueError(
                f"'{ENABLE_FIELD}' must be a boolean, got "
                f"{type(value).__name__} {value!r}."
            )
        return value

    @field_validator(WINDOW_FIELD, mode="before")
    @classmethod
    def _reject_invalid_window(cls, value: Any) -> Any:
        """Reject a non-integer or out-of-range window instead of coercing it.

        ``True`` would otherwise become ``1``, ``3.0`` would be truncated and
        ``"3"`` parsed; the constructor rejects all of them, and the upper
        bound keeps a window from inflating the prompt without limit.

        Parameters
        ----------
        value : Any
            Raw field value.

        Returns
        -------
        Any
            The unchanged value when it is a real ``int`` within bounds.

        Raises
        ------
        ValueError
            If the value is not a real ``int`` or lies outside
            ``[1, MAX_EXPAND_WINDOW]``.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"'{WINDOW_FIELD}' must be an integer, got "
                f"{type(value).__name__} {value!r}."
            )
        if value < 1 or value > MAX_EXPAND_WINDOW:
            raise ValueError(
                f"'{WINDOW_FIELD}' must be between 1 and {MAX_EXPAND_WINDOW}, "
                f"got {value}."
            )
        return value
