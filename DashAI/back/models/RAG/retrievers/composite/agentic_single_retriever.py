"""Agentic single retriever.

Takes exactly one child retriever and delegates retrieval to it. After each
round (except the last) the retriever asks its language model whether the
accumulated pool is sufficient; when it is not, the model's
``call_retrievers`` value asks for that many *additional* chunks. The retriever
is *blind* to its child's identity: the prompt never names the child beyond the
generic request, it just asks for more chunks. The child is then called with its
cumulative contributed size and only identities it had not contributed before
enter the pool.

The schema placeholders come from :mod:`DashAI.back.models.RAG.RAG_defaults`:
``children`` seeds the default hybrid retriever and ``llm_model`` seeds the
default RAG function-calling LLM. Both are ordinary, fully modifiable values.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Set, Tuple

from DashAI.back.core.schema_fields import (
    component_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MAX_ITERS,
    MAX_FUNCTION_CALL_TRIALS,
    default_agentic_retriever_prompt,
    default_function_calling_llm,
    default_hybrid_retriever,
)
from DashAI.back.models.RAG.retrievers.composite.agentic_retriever import (
    AgenticRetriever,
    IncrementalFetch,
    plan_incremental_fetch,
)
from DashAI.back.models.RAG.retrievers.composite.agentic_retriever_support import (
    LLM_RETRIEVER_CATEGORY,
)
from DashAI.back.models.RAG.retrievers.composite.evaluation_output import (
    RetrievalVerdict,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_pool import (
    ChunkKey,
    RetrievalPool,
    chunk_key,
)
from DashAI.back.models.RAG.retrievers.exceptions import CompositeValidationError
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CALL_RETRIEVERS_KEY,
    DISCARD_KEY,
    REQUEST_CHUNKS_KEY,
    SUFFICIENT_KEY,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    RetrievalExpansionSchema,
)


class AgenticSingleRetrieverSchema(RetrievalExpansionSchema):
    """Schema for :class:`AgenticSingleRetriever`.

    Attributes:
        children: Exactly one child retriever that is delegated to. Defaults to
            the default hybrid retriever; the value is fully modifiable.
        max_chunks: Maximum number of chunks the pool may hold.
        max_iters: Maximum number of retrieval rounds (judgements = iters - 1).
        prompt: The agentic retriever prompt component.
        llm_model: The text-to-text model that judges sufficiency. Defaults to
            the default RAG function-calling LLM; the value is fully modifiable.
        function_call_max_trials: Maximum number of evaluation attempts, the
            first call included. Both routes are retried on an unusable verdict.
    """

    children: schema_field(
        list_field(component_field(parent="BaseRetriever"), min_items=1, max_items=1),
        placeholder=[default_hybrid_retriever()],
        description=MultilingualString(
            en="The single child retriever that is delegated to. The retriever"
            " is blind to its identity: the prompt never names it. Defaults to"
            " the default hybrid retriever; you can change it.",
            es="El único recuperador hijo al que se delega. El recuperador es"
            " ciego a su identidad: el prompt nunca lo nombra. Por defecto usa"
            " el recuperador híbrido predeterminado; puedes cambiarlo.",
            pt="O único recuperador filho ao qual se delega. O recuperador é"
            " cego à sua identidade: o prompt nunca o nomeia. Por padrão usa o"
            " recuperador híbrido padrão; você pode alterá-lo.",
            de="Der einzige Kind-Retriever, an den delegiert wird. Der"
            " Retriever ist blind gegenüber seiner Identität: der Prompt nennt"
            " ihn nie. Standardmäßig wird der hybride Standard-Retriever"
            " verwendet; er ist änderbar.",
            zh=(
                "被委派的唯一子检索器。该检索器对其身份不可见：提示词从不提及它。"
                "默认为默认混合检索器，可随时修改。"
            ),
        ),
    )  # type: ignore

    max_chunks: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_MAX_CHUNKS,
        description=MultilingualString(
            en="Maximum number of chunks the accumulated pool may hold.",
            es="Número máximo de fragmentos que puede contener el conjunto acumulado.",
            pt="Número máximo de trechos que o conjunto acumulado pode conter.",
            de="Maximale Anzahl von Fragmenten im gesammelten Pool.",
            zh="累积池可容纳的最大片段数量。",
        ),
    )  # type: ignore

    max_iters: schema_field(
        int_field(gt=0),
        placeholder=DEFAULT_MAX_ITERS,
        description=MultilingualString(
            en="Maximum number of retrieval rounds. The final round is not"
            " judged, so there are at most this many minus one LLM calls.",
            es="Número máximo de rondas de recuperación. La ronda final no se"
            " evalúa, por lo que hay como máximo este número menos una llamadas"
            " al LLM.",
            pt="Número máximo de rodadas de recuperação. A rodada final não é"
            " avaliada, portanto há no máximo esse número menos uma chamadas ao"
            " LLM.",
            de="Maximale Anzahl von Abrufrunden. Die letzte Runde wird nicht"
            " bewertet, also höchstens diese Zahl minus eins LLM-Aufrufe.",
            zh="最大检索轮数。最后一轮不评估，因此最多有该数量减一次 LLM 调用。",
        ),
    )  # type: ignore

    function_call_max_trials: schema_field(
        int_field(ge=1, le=MAX_FUNCTION_CALL_TRIALS, strict=True),
        placeholder=DEFAULT_FUNCTION_CALL_MAX_TRIALS,
        description=MultilingualString(
            en="Maximum number of function-calling evaluation attempts,"
            " including the first. When the verdict is unusable or has no valid"
            " operation left, the evaluation is retried until this limit is"
            " reached.",
            es="Número máximo de intentos de evaluación mediante llamada a"
            " funciones, incluido el primero. Cuando el veredicto es inutilizable"
            " o no queda ninguna operación válida, la evaluación se reintenta"
            " hasta alcanzar este límite.",
            pt="Número máximo de tentativas de avaliação por chamada de função,"
            " incluindo a primeira. Quando o veredicto é inutilizável ou não resta"
            " nenhuma operação válida, a avaliação é repetida até atingir esse"
            " limite.",
            de="Maximale Anzahl von Bewertungsversuchen über Funktionsaufrufe,"
            " einschließlich des ersten. Wenn das Urteil unbrauchbar ist oder keine"
            " gültige Operation übrig bleibt, wird die Bewertung bis zu diesem"
            " Limit wiederholt.",
            zh="通过函数调用进行评估的最大尝试次数，包括首次尝试。当判定不可用或没有剩余"
            "有效操作时，会重试评估直到达到此限制。",
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
        component_field(parent="AgenticRetrieverPrompt"),
        placeholder=default_agentic_retriever_prompt(),
        description=MultilingualString(
            en="The prompt used to judge whether the retrieved chunks suffice.",
            es="El prompt usado para juzgar si los fragmentos recuperados son"
            " suficientes.",
            pt="O prompt usado para julgar se os trechos recuperados são suficientes.",
            de="Der Prompt, um zu beurteilen, ob die abgerufenen Fragmente ausreichen.",
            zh="用于判断已检索片段是否充分的提示词。",
        ),
    )  # type: ignore

    llm_model: schema_field(
        component_field(parent="TextToTextGenerationTaskModel"),
        placeholder=default_function_calling_llm(),
        description=MultilingualString(
            en="The language model that judges retrieval sufficiency. Defaults"
            " to the default RAG function-calling LLM; you can change it.",
            es="El modelo de lenguaje que juzga la suficiencia de la"
            " recuperación. Por defecto usa el LLM de llamada a funciones RAG"
            " predeterminado; puedes cambiarlo.",
            pt="O modelo de linguagem que julga a suficiência da recuperação."
            " Por padrão usa o LLM de chamada de funções RAG padrão; você pode"
            " alterá-lo.",
            de="Das Sprachmodell, das die Abrufsuffizienz beurteilt."
            " Standardmäßig wird das RAG-Standard-LLM für Funktionsaufrufe"
            " verwendet; es ist änderbar.",
            zh=("判断检索充分性的语言模型。默认为默认 RAG 函数调用 LLM，可随时修改。"),
        ),
    )  # type: ignore


class AgenticSingleRetriever(AgenticRetriever):
    """Iteratively deepens a single child's retrieval under LLM supervision.

    Round 1 delegates to the child with no size override (its own configuration
    drives). After each round but the last, the pool is judged; an insufficient
    verdict's ``call_retrievers`` value asks for that many *additional* chunks.
    The child is then called with its cumulative contributed size — the
    identities it already contributed plus the new request, capped by
    ``max_chunks`` plus the discarded slots — and only identities it had not
    contributed before enter the pool, taken in the child's own ranking order,
    so its highest-ranked unseen chunks are the ones added. Identity tracking
    keeps a child that ignores ``top_k`` or reorders its results from being
    starved; a response without unseen identities adds nothing, and the bounded
    ``max_iters`` still ends the loop.

    A composite child interprets that size under its own contract. The default
    hybrid child keeps its configured budget and may therefore fill the pool
    before the first judgement; raise ``max_chunks`` or choose a child that
    honours the requested cumulative size when deeper rounds are required.
    """

    SCHEMA = AgenticSingleRetrieverSchema
    CATEGORY: MultilingualString = LLM_RETRIEVER_CATEGORY
    DISPLAY_NAME: str = MultilingualString(
        en="Agentic Single Retriever",
        es="Recuperador Agéntico Único",
        pt="Retriever Agêntico Único",
        de="Agentischer Einzel-Retriever",
        zh="智能体单检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Delegates to one child retriever and iteratively deepens it: the"
        " agentic retriever decides whether the pool suffices and how many"
        " additional chunks to retrieve next.",
        es="Delega en un recuperador hijo y lo profundiza iterativamente: el"
        " recuperador agéntico decide si el conjunto es suficiente y cuántos"
        " fragmentos adicionales recuperar después.",
        pt="Delega a um recuperador filho e aprofunda iterativamente: o"
        " retriever agêntico decide se o conjunto é suficiente e quantos trechos"
        " adicionais recuperar em seguida.",
        de="Delegiert an einen Kind-Retriever und vertieft ihn iterativ: der"
        " agentische Retriever entscheidet, ob der Pool ausreicht und wie viele"
        " zusätzliche Fragmente als Nächstes abzurufen sind.",
        zh=(
            "委派给一个子检索器并迭代加深：由智能体检索器决定池是否充分"
            "以及下一步额外检索多少片段。"
        ),
    )

    EXPECTED_FUNCTION: ClassVar[str] = "evaluate_agentic_retrieval"
    FUNCTION_DESCRIPTION: ClassVar[str] = (
        "Decide whether the retrieved chunks are sufficient to answer the user "
        "message. Calling retrievers is not mandatory every round: when the "
        "pool suffices, set sufficient to true and omit all actions; when it "
        "does not, request chunks, call retrievers, or both. "
        "request_specific_chunks adds specific chunks to the pool even if no "
        "retriever returned them, discard_specific_chunks removes them, the two "
        "are mutually exclusive for the same chunk, and every chunk not "
        "mentioned is preserved. call_retrievers maps 1-based retriever indices "
        "to the number of additional chunks to retrieve next (only index 1 is "
        "valid here); chunks that retriever already returned are not counted "
        "again. Any configured top_k shown in the retriever catalog is the "
        "child's default, not a cumulative-call ceiling. Respect the maximum "
        "pool size and the remaining free slots. The "
        "value is an additional-chunk count, not a final absolute size; the "
        "retriever enforces the hard pool cap. Every retriever index and chunk "
        "position must be valid, never request and discard the same chunk, "
        "leave free capacity when calling retrievers, and do not leave the pool "
        "empty without a retriever call or chunk request. Chunks not mentioned "
        "stay in the pool exactly as they are, except when the maximum capacity "
        "forces out older non-requested chunks; requested chunks take priority. "
        "Invalid decisions are rejected and must be retried."
    )
    FUNCTION_PARAMETERS: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            SUFFICIENT_KEY: {
                "type": "boolean",
                "description": (
                    "Whether the retrieved chunks suffice to answer the user "
                    "message. When true, omit all actions."
                ),
            },
            CALL_RETRIEVERS_KEY: {
                "type": "object",
                "additionalProperties": {"type": "integer", "minimum": 1},
                "description": (
                    "Optional when insufficient: maps the 1-based retriever "
                    "index (only 1 is valid) to the number of ADDITIONAL chunks "
                    "to retrieve next. Chunks this retriever already returned "
                    "are not counted again. Not required every round."
                ),
            },
            REQUEST_CHUNKS_KEY: {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "description": (
                    "Maps document ids to chunk positions to add to the pool "
                    "even if no retriever returned them. Mutually exclusive with "
                    f"'{DISCARD_KEY}' for the same chunk."
                ),
            },
            DISCARD_KEY: {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "description": (
                    "Maps document ids to chunk positions to remove from the "
                    "pool even if a retriever returned them. Mutually exclusive "
                    f"with '{REQUEST_CHUNKS_KEY}' for the same chunk."
                ),
            },
            RAG_PROGRESS_MESSAGE_KEY: {
                "type": "string",
                "description": (
                    "Optional one short user-facing sentence in the prompt "
                    "language describing what you did."
                ),
            },
            RAG_PROGRESS_JUSTIFICATION_KEY: {
                "type": "string",
                "description": (
                    "Optional one short sentence in the prompt language "
                    "explaining why you did it."
                ),
            },
        },
        "required": [SUFFICIENT_KEY],
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the single retriever and enforce a single child.

        Parameters
        ----------
        **kwargs
            The common agentic retriever parameters.

        Raises
        ------
        CompositeValidationError
            If the retriever is not configured with exactly one child.
        """
        super().__init__(**kwargs)
        if len(self._children) != 1:
            raise CompositeValidationError(
                "AgenticSingleRetriever requires exactly one child retriever, "
                f"got {len(self._children)}."
            )

    def retrieve(self, query: str, **kwargs: Any) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve by delegating to the child and iteratively deepening.

        Parameters
        ----------
        query : str
            The search query string.
        **kwargs
            Unused; additional chunk counts come from the LLM verdicts.

        Returns
        -------
        Tuple[List[Chunk], Dict[str, Any]]
            The final pool (at most ``max_chunks`` chunks) and this retriever's
            trace node, whose ``children`` holds every delegated child node and
            whose ``rounds`` holds one summary per retrieval round.

        Raises
        ------
        RAGRetrieverEvaluationError
            If a verdict stays unusable after retries. Any invalid retriever
            index, chunk reference, contradictory action, capacity violation or
            empty-refill-less decision rejects the whole verdict and is retried.
        """
        child = self._children[0]
        context = RetrievalContext.from_retriever(self)
        pool = RetrievalPool(self.max_chunks, context)
        child_nodes: List[Dict[str, Any]] = []
        rounds: List[Dict[str, Any]] = []
        contributed: Set[ChunkKey] = set()
        pending_fetch: IncrementalFetch | None = None
        should_delegate = True

        for round_index in range(self.max_iters):
            delegating = should_delegate and pool.size() < self.max_chunks
            entry = self._build_entry(child, round_index, pending_fetch, delegating)
            if delegating:
                self._delegate_round(
                    child,
                    query,
                    pool,
                    pending_fetch,
                    contributed,
                    entry,
                    child_nodes,
                )
            elif should_delegate:
                # The pool is already full; still evaluate so request/discard
                # actions can change its composition.
                should_delegate = False
                pending_fetch = None
            rounds.append(entry)

            if round_index == self.max_iters - 1:
                break

            verdict, prepared = self._evaluate_with_pool(
                query,
                pool,
                context,
                round_number=round_index + 1,
                max_rounds=max(self.max_iters - 1, 1),
            )
            self._record_verdict(entry, verdict)
            if verdict.sufficient:
                self._emit_verdict(entry, verdict)
                break
            if prepared is None:
                raise RAGRetrieverEvaluationError(
                    "An insufficient verdict did not produce an applied pool."
                )
            pool = prepared
            self._emit_verdict(entry, verdict)
            pending_fetch, should_delegate = self._next_round_state(
                verdict, pool, contributed
            )

        pool_chunks = self._apply_retrieval_expansion(pool.materialize())
        return pool_chunks, self._build_trace(pool_chunks, child_nodes, rounds)

    def _delegate_round(
        self,
        child: Any,
        query: str,
        pool: RetrievalPool,
        fetch: IncrementalFetch | None,
        contributed: Set[ChunkKey],
        entry: Dict[str, Any],
        child_nodes: List[Dict[str, Any]],
    ) -> None:
        """Delegate one depth round and merge only unseen chunk identities.

        The initial round (``fetch is None``) seeds the pool with the child's
        own result. Later rounds call the child with the cumulative
        ``fetch.top_k`` and merge only up to ``fetch.additional`` identities the
        child had not contributed before, in response order. Raw response
        lengths are never used as bookkeeping, so an over-returning child
        contributes its leading unseen chunks instead of its tail and a
        reordering child cannot skip unseen chunks or be starved. When the
        response contains no unseen identity, nothing is added and the round
        simply ends; no retry or artificial chunk is created.

        Parameters
        ----------
        child : Any
            The child retriever.
        query : str
            The search query string.
        pool : RetrievalPool
            The real pool receiving the newly fetched chunks.
        fetch : IncrementalFetch | None
            The planned cumulative fetch, or ``None`` for the initial round.
        contributed : Set[ChunkKey]
            Identities already contributed by the child. Updated in place.
        entry : Dict[str, Any]
            The round trace entry to update.
        child_nodes : List[Dict[str, Any]]
            The accumulated child trace nodes.

        Returns
        -------
        None
            The pool, the identity history and the trace entry are updated.
        """
        top_k = None if fetch is None else fetch.top_k
        chunks, node = self._delegate(child, query, top_k)
        child_nodes.append(node)
        before = pool.size()
        new_chunks = chunks if fetch is None else fetch.select_new(chunks, contributed)
        pool.add(new_chunks)
        contributed.update(chunk_key(chunk) for chunk in new_chunks)
        entry["returned"] = len(chunks)
        entry["added"] = pool.size() - before

    def _next_round_state(
        self,
        verdict: RetrievalVerdict,
        pool: RetrievalPool,
        contributed: Set[ChunkKey],
    ) -> Tuple[IncrementalFetch | None, bool]:
        """Return the next cumulative fetch plan and whether to delegate.

        The model asks for *additional* chunks. The plan's cumulative size is
        the identities the child already contributed plus that request, capped
        at ``max_chunks`` plus the discarded slots: discarded chunks still
        occupy the child's ranking, so replacing one requires fetching past the
        pool cap.

        Parameters
        ----------
        verdict : RetrievalVerdict
            The finalized insufficient verdict.
        pool : RetrievalPool
            The adopted pool for the next round.
        contributed : Set[ChunkKey]
            Identities the child already contributed.

        Returns
        -------
        Tuple[IncrementalFetch | None, bool]
            The cumulative fetch plan and whether to delegate. The fetch is
            ``None`` and delegation stops when the verdict asks for no chunk or
            the child's remaining usable prefix cannot add one.
        """
        calls = verdict.call_retrievers
        if 1 not in calls:
            return None, False
        fetch = plan_incremental_fetch(
            len(contributed),
            calls[1],
            self.max_chunks + pool.discarded_count(),
        )
        if fetch.additional <= 0:
            return None, False
        return fetch, True

    def _build_entry(
        self,
        child: Any,
        round_index: int,
        fetch: IncrementalFetch | None,
        delegating: bool,
    ) -> Dict[str, Any]:
        """Build the trace entry for one depth round.

        Parameters
        ----------
        child : Any
            The delegated child retriever.
        round_index : int
            Zero-based round index.
        fetch : IncrementalFetch | None
            The planned cumulative fetch for this round, if delegating.
        delegating : bool
            Whether this round delegates retrieval to the child.

        Returns
        -------
        Dict[str, Any]
            A JSON-serializable round summary with the action maps initialized.
            ``requested_top_k`` is the actual cumulative call size, ``returned``
            is the raw child response count and ``added`` is the number of
            chunks the pool gained from this call.
        """
        requested_top_k = fetch.top_k if fetch is not None and delegating else None
        return {
            "round": round_index + 1,
            "name": type(child).__name__,
            "requested_top_k": requested_top_k,
            "returned": 0,
            "added": 0,
            "verdict": None,
            CALL_RETRIEVERS_KEY: {},
            REQUEST_CHUNKS_KEY: {},
            DISCARD_KEY: {},
        }

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
        return self._children[0].score_chunks(chunk_ids, query)
