"""LLM filter composite retriever.

Takes exactly one child retriever and delegates the candidate retrieval to it
with a ``k1`` size hint. When more than ``top_k`` unique candidates come back,
a language model is asked to select the best ``top_k`` indices through the
``select_best_chunks`` function call. When the candidate set already fits
``top_k`` (or is empty) the model is not called at all.

The retriever caps the child's output to ``k1`` and deduplicates it by
``(document_id, document_position)`` before evaluating it, so a child that
ignores the size hint can never grow the candidate set beyond its budget.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from DashAI.back.core.schema_fields import (
    component_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverCompositeValidationError,
)
from DashAI.back.models.RAG.progress_utils import report_progress
from DashAI.back.models.RAG.prompts.evaluation import LLMFilterPrompt
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
    RAG_PROGRESS_STAGE_RETRIEVING,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FILTER_K1,
    DEFAULT_FILTER_TOP_K,
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    MAX_FUNCTION_CALL_TRIALS,
    default_function_calling_llm,
    default_hybrid_retriever,
    default_llm_filter_prompt,
)
from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.filter_evaluator import (
    FilterEvaluator,
)
from DashAI.back.models.RAG.retrievers.composite.filter_selection import (
    ChunkSelection,
)
from DashAI.back.models.RAG.retrievers.composite.llm_retriever_support import (
    close_llm,
    pop_positive_int,
    pop_required,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    DROPPED_OPERATIONS_KEY,
    SELECTED_CHUNKS_KEY,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    RetrievalExpansionSchema,
)
from DashAI.back.models.RAG.retrievers.trace_utils import retriever_trace

#: Schema/param key names hoisted to avoid magic strings.
_PARAM_K1 = "k1"
_PARAM_TOP_K = "top_k"
_PARAM_PROMPT = "prompt"
_PARAM_LLM_MODEL = "llm_model"
_PARAM_FUNCTION_CALL_MAX_TRIALS = "function_call_max_trials"

#: Function name the model must call.
SELECT_BEST_CHUNKS_FUNCTION = "select_best_chunks"

logger = logging.getLogger(__name__)

#: Trace summary keys.
_SELECTION_TRACE_KEY = "selection"
_SELECTION_CANDIDATES_KEY = "candidates"
_SELECTION_TOP_K_KEY = "top_k"
_SELECTION_SELECTED_KEY = "selected"
_SELECTION_LLM_USED_KEY = "llm_used"


class LLMFilterRetrieverSchema(RetrievalExpansionSchema):
    """Schema for :class:`LLMFilterRetriever`.

    Attributes:
        children: Exactly one child retriever that produces the candidates.
        k1: Number of candidates fetched from the child.
        top_k: Number of best chunks selected by the model.
        function_call_max_trials: Maximum number of selection attempts.
        prompt: The filter prompt component.
        llm_model: The text-to-text model that selects the best chunks.
    """

    children: schema_field(
        list_field(component_field(parent="BaseRetriever"), min_items=1, max_items=1),
        placeholder=[default_hybrid_retriever()],
        description=MultilingualString(
            en="The single child retriever that supplies the candidate chunks."
            " Defaults to the default hybrid retriever; you can change it.",
            es="El único recuperador hijo que aporta los fragmentos candidatos."
            " Por defecto usa el recuperador híbrido predeterminado; puedes"
            " cambiarlo.",
            pt="O único recuperador filho que fornece os trechos candidatos."
            " Por padrão usa o recuperador híbrido padrão; você pode alterá-lo.",
            de="Der einzige Kind-Retriever, der die Kandidatenfragmente liefert."
            " Standardmäßig wird der hybride Standard-Retriever verwendet; er"
            " ist änderbar.",
            zh="提供候选片段的唯一子检索器。默认为默认混合检索器，可随时修改。",
        ),
    )  # type: ignore

    k1: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_FILTER_K1,
        description=MultilingualString(
            en="Number of candidate chunks fetched from the child retriever.",
            es="Número de fragmentos candidatos obtenidos del recuperador hijo.",
            pt="Número de trechos candidatos obtidos do recuperador filho.",
            de="Anzahl der vom Kind-Retriever abgerufenen Kandidatenfragmente.",
            zh="从子检索器获取的候选片段数量。",
        ),
        alias=MultilingualString(
            en="Candidate chunks (k1)",
            es="Fragmentos candidatos (k1)",
            pt="Trechos candidatos (k1)",
            de="Kandidatenfragmente (k1)",
            zh="候选片段（k1）",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_FILTER_TOP_K,
        description=MultilingualString(
            en="Number of best chunks the model selects. Cannot exceed k1.",
            es="Número de mejores fragmentos que selecciona el modelo. No puede"
            " superar k1.",
            pt="Número de melhores trechos que o modelo seleciona. Não pode"
            " exceder k1.",
            de="Anzahl der vom Modell ausgewählten besten Fragmente. Darf k1"
            " nicht überschreiten.",
            zh="模型选择的最佳片段数量，不能超过 k1。",
        ),
        alias=MultilingualString(
            en="Selected chunks (top-k)",
            es="Fragmentos seleccionados (top-k)",
            pt="Trechos selecionados (top-k)",
            de="Ausgewählte Fragmente (Top-k)",
            zh="已选片段（top-k）",
        ),
    )  # type: ignore

    function_call_max_trials: schema_field(
        int_field(ge=1, le=MAX_FUNCTION_CALL_TRIALS, strict=True),
        placeholder=DEFAULT_FUNCTION_CALL_MAX_TRIALS,
        description=MultilingualString(
            en="Maximum number of selection attempts on the configured route,"
            " including the first. Malformed or invalid selections are retried"
            " up to this limit; unexpected backend exception types propagate"
            " instead of being retried.",
            es="Número máximo de intentos de selección en la ruta configurada,"
            " incluido el primero. Las selecciones malformadas o inválidas se"
            " reintentan hasta este límite; los tipos de excepción inesperados"
            " del backend se propagan en lugar de reintentarse.",
            pt="Número máximo de tentativas de seleção na rota configurada,"
            " incluindo a primeira. Seleções malformadas ou inválidas são"
            " repetidas até este limite; tipos de exceção inesperados do backend"
            " são propagados em vez de repetidos.",
            de="Maximale Anzahl von Auswahlversuchen auf der konfigurierten"
            " Route, einschließlich des ersten. Fehlerhafte oder ungültige"
            " Auswahlen werden bis zu diesem Limit wiederholt; unerwartete"
            " Backend-Ausnahmetypen werden weitergereicht und nicht wiederholt.",
            zh="在配置路由上的选择尝试最大次数，包括首次尝试。格式错误或无效的选择会重试到此"
            "限制；意外的后端异常类型会向上传播而不重试。",
        ),
        alias=MultilingualString(
            en="Function call max trials",
            es="Máximo de intentos de llamada a funciones",
            pt="Máximo de tentativas de chamada de função",
            de="Max. Funktionsaufrufversuche",
            zh="函数调用最大尝试次数",
        ),
    ) = DEFAULT_FUNCTION_CALL_MAX_TRIALS  # type: ignore

    prompt: schema_field(
        component_field(parent="LLMFilterPrompt"),
        placeholder=default_llm_filter_prompt(),
        description=MultilingualString(
            en="The prompt used to select the best candidate chunks.",
            es="El prompt usado para seleccionar los mejores fragmentos candidatos.",
            pt="O prompt usado para selecionar os melhores trechos candidatos.",
            de="Der Prompt zur Auswahl der besten Kandidatenfragmente.",
            zh="用于选择最佳候选片段的提示词。",
        ),
    )  # type: ignore

    llm_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder=default_function_calling_llm(),
        description=MultilingualString(
            en="The language model that selects the best chunks. Defaults to the"
            " default RAG function-calling LLM; you can change it.",
            es="El modelo de lenguaje que selecciona los mejores fragmentos. Por"
            " defecto usa el LLM de llamada a funciones RAG predeterminado;"
            " puedes cambiarlo.",
            pt="O modelo de linguagem que seleciona os melhores trechos. Por"
            " padrão usa o LLM de chamada de funções RAG padrão; você pode"
            " alterá-lo.",
            de="Das Sprachmodell, das die besten Fragmente auswählt."
            " Standardmäßig wird das RAG-Standard-LLM für Funktionsaufrufe"
            " verwendet; es ist änderbar.",
            zh="选择最佳片段的语言模型。默认为默认 RAG 函数调用 LLM，可随时修改。",
        ),
    )  # type: ignore


class LLMFilterRetriever(CompositeRetriever):
    """Selects the best ``top_k`` candidates from a child with an LLM.

    The child is queried with ``k1`` as a retrieval-size hint. Its output is
    deduplicated and capped to ``k1``; when it already fits ``top_k`` the model
    is skipped and the candidates are returned unchanged. Otherwise the model
    receives the numbered candidates and must return up to ``top_k`` 1-based
    indices through the ``select_best_chunks`` function call. The configured
    ``llm_model`` must support function calling.
    """

    SCHEMA = LLMFilterRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="LLM Filter Retriever",
        es="Recuperador de Filtro LLM",
        pt="Retriever de Filtro LLM",
        de="LLM-Filter-Retriever",
        zh="LLM 过滤检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Retrieves k1 candidates from one child retriever and uses an LLM to"
        " select the best top-k chunks with a function call.",
        es="Recupera k1 candidatos de un recuperador hijo y usa un LLM para"
        " seleccionar los mejores top-k fragmentos con una llamada a función.",
        pt="Recupera k1 candidatos de um recuperador filho e usa um LLM para"
        " selecionar os melhores top-k trechos com uma chamada de função.",
        de="Ruft k1 Kandidaten von einem Kind-Retriever ab und wählt mit einem"
        " LLM die besten Top-k-Fragmente über einen Funktionsaufruf aus.",
        zh=(
            "从一个子检索器获取 k1 个候选，并使用 LLM 通过函数调用选择最佳的"
            " top-k 片段。"
        ),
    )

    REPRESENTATION = MultilingualString(
        en="k1 {k1} · top-k {top_k} · {prompt}",
        es="candidatos {k1} · top-k {top_k} · {prompt}",
        pt="candidatos {k1} · top-k {top_k} · {prompt}",
        de="k1 {k1} · Top-k {top_k} · {prompt}",
        zh="k1 {k1} · 前 k {top_k} · {prompt}",
    )

    #: Nested component references the factories must resolve before construction.
    COMPONENT_PARAMS: tuple[str, ...] = (_PARAM_LLM_MODEL, _PARAM_PROMPT)

    #: Prompt family this retriever accepts.
    EVALUATION_PROMPT_BASE = LLMFilterPrompt

    EXPECTED_FUNCTION: ClassVar[str] = SELECT_BEST_CHUNKS_FUNCTION
    FUNCTION_DESCRIPTION: ClassVar[str] = (
        "Select the best candidate chunks for answering the user message. "
        "selected_chunks is required: 1-based indices into the numbered "
        "candidate list, best first, unique, in-range, at most top_k entries. "
        "Invalid or out-of-range selections are rejected and must be retried. "
        "message and justification are optional short narrative fields."
    )
    FUNCTION_PARAMETERS: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            SELECTED_CHUNKS_KEY: {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "description": (
                    "1-based indices into the numbered candidate list, best "
                    "first, unique, at most top_k entries."
                ),
            },
            RAG_PROGRESS_MESSAGE_KEY: {
                "type": "string",
                "description": (
                    "Optional one short user-facing sentence in the prompt "
                    "language describing what you selected."
                ),
            },
            RAG_PROGRESS_JUSTIFICATION_KEY: {
                "type": "string",
                "description": (
                    "Optional one short sentence in the prompt language "
                    "explaining your selection."
                ),
            },
        },
        "required": [SELECTED_CHUNKS_KEY],
    }

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Return the candidate and final budget paths."""
        return {_PARAM_K1: _PARAM_K1, _PARAM_TOP_K: _PARAM_TOP_K}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the filter retriever and validate its budgets.

        Parameters
        ----------
        **kwargs
            Must contain ``children`` (handled by the composite base), ``k1``,
            ``top_k``, ``prompt`` and ``llm_model``. ``function_call_max_trials``
            is optional and defaults to
            :data:`DEFAULT_FUNCTION_CALL_MAX_TRIALS`.

        Raises
        ------
        CompositeValidationError
            If there is not exactly one child, a budget is not a positive
            integer, ``top_k`` exceeds ``k1``, or ``llm_model`` does not support
            function calling.
        RAGRetrieverMissingParameterError
            If ``prompt`` or ``llm_model`` is absent.
        """
        super().__init__(**kwargs)
        self._single_child()
        self._k1 = pop_positive_int(
            self.params,
            _PARAM_K1,
            component_label="LLM filter retriever",
        )
        self._top_k = pop_positive_int(
            self.params,
            _PARAM_TOP_K,
            component_label="LLM filter retriever",
        )
        if self._top_k > self._k1:
            raise RAGRetrieverCompositeValidationError(
                f"'{_PARAM_TOP_K}' must not exceed '{_PARAM_K1}', got "
                f"top_k={self._top_k} and k1={self._k1}."
            )
        self.function_call_max_trials = pop_positive_int(
            self.params,
            _PARAM_FUNCTION_CALL_MAX_TRIALS,
            component_label="LLM filter retriever",
            default=DEFAULT_FUNCTION_CALL_MAX_TRIALS,
            maximum=MAX_FUNCTION_CALL_TRIALS,
        )
        self.prompt = pop_required(
            self.params,
            _PARAM_PROMPT,
            component_label="LLM filter retriever",
        )
        self.llm_model = pop_required(
            self.params,
            _PARAM_LLM_MODEL,
            component_label="LLM filter retriever",
        )
        if not self.llm_model.supports_function_calling():
            raise RAGRetrieverCompositeValidationError(
                f"{type(self).__name__} requires an llm_model with function "
                f"calling support; {type(self.llm_model).__name__} does not "
                "support function calling."
            )
        self._evaluator = FilterEvaluator(
            self.prompt,
            self.llm_model,
            self.EXPECTED_FUNCTION,
            self.FUNCTION_DESCRIPTION,
            self.FUNCTION_PARAMETERS,
            self.function_call_max_trials,
        )

    @property
    def retrieval_top_k(self) -> int:
        """Return the number of selected chunks (``top_k``)."""
        return self._top_k

    def retrieve(self, query: str, **kwargs: Any) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve candidates from the child and select the best ones.

        Parameters
        ----------
        query : str
            The search query string.
        **kwargs
            Ignored. A parent composite may pass a ``top_k`` hint, but the
            filter retriever keeps its own configured ``k1`` candidate budget
            and ``top_k`` final budget.

        Returns
        -------
        Tuple[List[Chunk], Dict[str, Any]]
            The selected chunks and this retriever's trace node, whose
            ``children`` holds the child node and whose ``selection`` holds a
            JSON-serializable summary of the filter decision. The result holds
            **at most** ``top_k`` chunks.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the selection stays unusable after the retry budget. Any invalid,
            duplicate or over-budget index rejects the whole selection and is
            retried; no partial selection is ever applied.
        """
        child = self._single_child()
        child_chunks, child_node = child.retrieve(query, top_k=self._k1)
        candidates = self._dedupe_candidates(child_chunks)
        selection: Optional[ChunkSelection] = None
        if not candidates:
            selected: List[Chunk] = []
        elif len(candidates) <= self._top_k:
            # The candidate set already fits the final budget: the model could
            # only reorder a list that is already the child's ranking, so the
            # call is skipped deliberately.
            selected = list(candidates)
        else:
            context = RetrievalContext.from_retriever(self)
            selection = self._evaluator.evaluate(
                query, candidates, self._top_k, context
            )
            self._report_selection_progress(selection)
            selected = [candidates[index - 1] for index in selection.selected_indices]

        summary = self._selection_summary(candidates, selected, selection)
        results = self._apply_retrieval_expansion(selected)
        return results, retriever_trace(
            self,
            results,
            children=[child_node],
            **{_SELECTION_TRACE_KEY: summary},
        )

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Score chunks by delegating to the single child.

        Parameters
        ----------
        chunk_ids : List[int]
            List of chunk IDs to score.
        query : str
            The search query string.

        Returns
        -------
        List[Tuple[int, float]]
            A list of ``(chunk_id, distance)`` tuples from the child.
        """
        return self._single_child().score_chunks(chunk_ids, query)

    def add(self, child: BaseRetriever) -> None:
        """Reject adding a child after construction.

        Parameters
        ----------
        child : BaseRetriever
            The child that would be added; ignored.

        Raises
        ------
        RAGRetrieverCompositeValidationError
            Always. The filter retriever requires exactly one child configured
            through the constructor.
        """
        raise RAGRetrieverCompositeValidationError(
            "LLMFilterRetriever requires exactly one child retriever configured"
            " via the constructor; add() is not supported."
        )

    def remove(self, child: BaseRetriever) -> None:
        """Reject removing the child after construction.

        Parameters
        ----------
        child : BaseRetriever
            The child that would be removed; ignored.

        Raises
        ------
        RAGRetrieverCompositeValidationError
            Always. The filter retriever requires exactly one child configured
            through the constructor.
        """
        raise RAGRetrieverCompositeValidationError(
            "LLMFilterRetriever requires exactly one child retriever configured"
            " via the constructor; remove() is not supported."
        )

    def _single_child(self) -> BaseRetriever:
        """Return the single child, re-validating the invariant.

        Returns
        -------
        BaseRetriever
            The configured child retriever.

        Raises
        ------
        RAGRetrieverCompositeValidationError
            If the child list was mutated to zero or multiple children.
        """
        if len(self._children) != 1:
            raise RAGRetrieverCompositeValidationError(
                "LLMFilterRetriever requires exactly one child retriever, "
                f"got {len(self._children)}."
            )
        return self._children[0]

    def close(self) -> None:
        """Release the selection LLM and then the child retriever.

        A failure while closing the LLM is logged rather than raised so cleanup
        never masks the retrieval failure that ended the stage; the children are
        still released through the composite base.

        Returns
        -------
        None
            Nothing.
        """
        close_llm(self.llm_model, type(self).__name__, "filter LLM", logger)
        super().close()

    def _dedupe_candidates(self, chunks: List[Chunk]) -> List[Chunk]:
        """Deduplicate and cap the child's output to ``k1``.

        Parameters
        ----------
        chunks : List[Chunk]
            Chunks returned by the child, in retrieval order.

        Returns
        -------
        List[Chunk]
            At most ``k1`` unique chunks, preserving first-seen order. Identity
            is ``(document_id, document_position)``.
        """
        seen: set[Tuple[int, int]] = set()
        unique: List[Chunk] = []
        for chunk in chunks:
            key = (chunk.document_id, chunk.document_position)
            if key in seen:
                continue
            seen.add(key)
            unique.append(chunk)
            if len(unique) >= self._k1:
                break
        return unique

    def _selection_summary(
        self,
        candidates: List[Chunk],
        selected: List[Chunk],
        selection: Optional[ChunkSelection],
    ) -> Dict[str, Any]:
        """Build the JSON-serializable selection summary for the trace.

        Parameters
        ----------
        candidates : List[Chunk]
            The deduplicated candidate chunks.
        selected : List[Chunk]
            The chunks returned to the caller.
        selection : ChunkSelection | None
            The model selection, or ``None`` when the LLM was not called.

        Returns
        -------
        Dict[str, Any]
            Candidate count, requested top-k, selected 1-based indices,
            ``llm_used``, the optional narrative and the dropped operations.
        """
        if selection is None:
            selected_indices = list(range(1, len(selected) + 1))
            message = ""
            justification = ""
            dropped: List[str] = []
        else:
            selected_indices = list(selection.selected_indices)
            message = selection.message
            justification = selection.justification
            dropped = list(selection.dropped_operations)
        return {
            _SELECTION_CANDIDATES_KEY: len(candidates),
            _SELECTION_TOP_K_KEY: self._top_k,
            _SELECTION_SELECTED_KEY: selected_indices,
            _SELECTION_LLM_USED_KEY: selection is not None,
            RAG_PROGRESS_MESSAGE_KEY: message,
            RAG_PROGRESS_JUSTIFICATION_KEY: justification,
            DROPPED_OPERATIONS_KEY: dropped,
        }

    def _report_selection_progress(self, selection: ChunkSelection) -> None:
        """Report the selection's optional narrative on the retrieving channel.

        Parameters
        ----------
        selection : ChunkSelection
            The validated selection, possibly carrying ``message`` and/or
            ``justification``.

        Returns
        -------
        None
            Nothing is emitted when the selection has no narrative.
        """
        if not selection.message and not selection.justification:
            return
        report_progress(
            RAG_PROGRESS_STAGE_RETRIEVING,
            message=selection.message,
            justification=selection.justification,
        )
