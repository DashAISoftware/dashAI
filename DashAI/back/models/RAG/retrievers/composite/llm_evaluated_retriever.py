"""Abstract base for LLM-evaluated composite retrievers.

Both concrete retrievers share the same idea: retrieve a pool of chunks, ask a
language model whether that pool is sufficient to answer the query, and — when
it is not — retrieve again according to the model's verdict. The language model
is a parameter *of the retriever itself* (not of the RAG pipeline). Any parse or
validation failure of the verdict raises; there are no silent fallbacks.

The verdict is obtained through ``generate_function_call`` with the subclass's
JSON schema, so the arguments shape is constrained by the backend. The
configured ``llm_model`` must support function calling.
Any invalid retriever index, chunk reference, contradictory operation, capacity
violation or empty-refill-less decision rejects the whole verdict and is retried
on the function-calling route up to ``function_call_max_trials`` attempts.
Verdict application is transactional: the pool is cloned, validated and only
then adopted, so a failed attempt never mutates the real pool.

Subclasses differ only in how they choose the *next* retrieval: the depth
retriever asks for a larger retrieval size from its single child, while the
ensemble retriever asks the model to pick which of its children to consult.
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any, Callable, ClassVar, Dict, List, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverCompositeValidationError,
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.progress_utils import report_progress
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
    RAG_PROGRESS_STAGE_RETRIEVING,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    MAX_FUNCTION_CALL_TRIALS,
)
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.evaluation_output import (
    RetrievalVerdict,
)
from DashAI.back.models.RAG.retrievers.composite.llm_retriever_support import (
    close_llm,
    pop_positive_int,
    pop_required,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_evaluator import (
    RetrievalEvaluator,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_pool import RetrievalPool
from DashAI.back.models.RAG.retrievers.composite.structured_output import (
    cap_errors,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CALL_RETRIEVERS_KEY,
    DISCARD_KEY,
    DROPPED_OPERATIONS_KEY,
    REQUEST_CHUNKS_KEY,
    unpack_retrieval_result,
)
from DashAI.back.models.RAG.retrievers.trace_utils import retriever_trace

log = logging.getLogger(__name__)

#: Schema/param key names hoisted to avoid magic strings.
_PARAM_MAX_ITERS = "max_iters"
_PARAM_MAX_CHUNKS = "max_chunks"
_PARAM_PROMPT = "prompt"
_PARAM_LLM_MODEL = "llm_model"
_PARAM_FUNCTION_CALL_MAX_TRIALS = "function_call_max_trials"

#: Trace round-entry keys hoisted to avoid magic strings.
_ENTRY_VERDICT_KEY = "verdict"
_ENTRY_APPLIED_KEY = "applied"


class LLMEvaluatedRetriever(CompositeRetriever, ABC):
    """Shared behaviour of the LLM-evaluated composite retrievers.

    Handles construction/validation of the common parameters, the delegation
    contract, the pool merge/cap rules and the prompt rendering + LLM call +
    verdict parsing pipeline. Concrete subclasses implement :meth:`retrieve` and
    :meth:`score_chunks`.

    Attributes:
        max_iters: Maximum number of retrieval rounds (``>= 1``).
        max_chunks: Maximum number of chunks the pool may hold (``>= 1``).
        prompt: The :class:`RetrievalSufficiencyPrompt` instance used to judge
            the pool. Required — no artificial default is assumed.
        llm_model: The :class:`TextToTextGenerationTaskModel` used to judge the
            pool. It must support function calling. Required — no artificial
            default is assumed.
        function_call_max_trials: Maximum number of evaluation attempts, the
            first call included. Unusable verdicts are retried on the
            function-calling route.
            Defaults to :data:`DEFAULT_FUNCTION_CALL_MAX_TRIALS`.
        EXPECTED_FUNCTION: The function name a function-calling model must call.
        FUNCTION_DESCRIPTION: Human-readable description of that function.
        FUNCTION_PARAMETERS: JSON schema of the function's arguments.
    """

    #: Nested ``{component, params}`` reference parameters the factories must
    #: resolve into live component instances before construction.
    COMPONENT_PARAMS: tuple[str, ...] = (_PARAM_LLM_MODEL, _PARAM_PROMPT)

    #: Function-calling contract declared by each concrete retriever.
    EXPECTED_FUNCTION: ClassVar[str] = ""
    FUNCTION_DESCRIPTION: ClassVar[str] = ""
    FUNCTION_PARAMETERS: ClassVar[Dict[str, Any]] = {}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the retriever with its common parameters.

        Parameters
        ----------
        **kwargs
            Must contain ``children`` (handled by the composite base),
            ``max_iters``, ``max_chunks``, ``prompt`` and ``llm_model``.
            ``function_call_max_trials`` is optional and defaults to
            :data:`DEFAULT_FUNCTION_CALL_MAX_TRIALS`.

        Raises
        ------
        RAGRetrieverMissingParameterError
            If ``max_iters``, ``max_chunks``, ``prompt`` or ``llm_model`` is
            absent.
        RAGRetrieverCompositeValidationError
            If ``max_iters``, ``max_chunks`` or ``function_call_max_trials`` is
            not a positive integer, or if ``llm_model`` does not support
            function calling.
        """
        super().__init__(**kwargs)
        self.max_iters = pop_positive_int(
            self.params,
            _PARAM_MAX_ITERS,
            component_label="LLM-evaluated retriever",
        )
        self.max_chunks = pop_positive_int(
            self.params,
            _PARAM_MAX_CHUNKS,
            component_label="LLM-evaluated retriever",
        )
        self.function_call_max_trials = pop_positive_int(
            self.params,
            _PARAM_FUNCTION_CALL_MAX_TRIALS,
            component_label="LLM-evaluated retriever",
            default=DEFAULT_FUNCTION_CALL_MAX_TRIALS,
            maximum=MAX_FUNCTION_CALL_TRIALS,
        )
        self.prompt = pop_required(
            self.params,
            _PARAM_PROMPT,
            component_label="LLM-evaluated retriever",
        )
        self.llm_model = pop_required(
            self.params,
            _PARAM_LLM_MODEL,
            component_label="LLM-evaluated retriever",
        )
        if not self.llm_model.supports_function_calling():
            raise RAGRetrieverCompositeValidationError(
                f"{type(self).__name__} requires an llm_model with function "
                f"calling support; {type(self.llm_model).__name__} does not "
                "support function calling."
            )
        self._evaluator = RetrievalEvaluator(
            self.prompt,
            self.llm_model,
            self.EXPECTED_FUNCTION,
            self.FUNCTION_DESCRIPTION,
            self.FUNCTION_PARAMETERS,
            self.function_call_max_trials,
        )

    REPRESENTATION = MultilingualString(
        en="max_iters {max_iters} · max_chunks {max_chunks} · {prompt}",
        es="máx. iteraciones {max_iters} · máx. fragmentos {max_chunks} · {prompt}",
        pt="máx. iterações {max_iters} · máx. trechos {max_chunks} · {prompt}",
        de="max. Iterationen {max_iters} · max. Chunks {max_chunks} · {prompt}",
        zh="最大迭代 {max_iters} · 最大片段 {max_chunks} · {prompt}",
    )

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Return the round and pool budget paths."""
        return {"max_iters": "max_iters", "max_chunks": "max_chunks"}

    def close(self) -> None:
        """Release the evaluation LLM and nested LLM-evaluated children.

        The LLM is closed when it exposes a ``close`` hook; a failure while
        closing it is suppressed so cleanup never masks the retrieval failure
        that ended the stage. Nested composites are released through the
        composite base, which also covers deeper LLM-evaluated descendants.

        Returns
        -------
        None
            Nothing.
        """
        close_llm(self.llm_model, type(self).__name__, "evaluation LLM", log)
        super().close()

    @property
    def retrieval_top_k(self) -> int:
        """Return the pool cap (``max_chunks``)."""
        return self.max_chunks

    def _delegate(
        self, child: Any, query: str, top_k: int | None
    ) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve from a child retriever under the shared delegation contract.

        ``top_k`` is a **retrieval-size hint**, not a hard final count. Unit
        children (BM25/TFIDF/dense) honour it as the number of candidates to
        return; composite children interpret it per their own contract, e.g. the
        cross-encoder treats it as a final count and the MMR reranker ignores it.
        That asymmetry is accepted and documented here rather than worked around
        at the call site.

        Parameters
        ----------
        child : BaseRetriever
            The child retriever to delegate to.
        query : str
            The search query string.
        top_k : int | None
            The retrieval-size hint, or ``None`` to let the child use its own
            configured size.

        Returns
        -------
        Tuple[List[Chunk], Dict[str, Any]]
            The child's ``(chunks, trace node)``.
        """
        if top_k is None:
            return unpack_retrieval_result(child.retrieve(query))
        return unpack_retrieval_result(child.retrieve(query, top_k=top_k))

    def _prepare_insufficient_verdict(
        self,
        pool: RetrievalPool,
        verdict: RetrievalVerdict,
    ) -> RetrievalPool:
        """Apply an insufficient verdict transactionally and validate capacity.

        The actions are applied to an isolated clone, so a rejected decision
        never mutates the real pool. Any invalid chunk reference, missing
        capacity for the requested retrievers, requested chunk that does not fit
        the cap, or empty-refill-less decision raises
        :class:`RAGRetrieverEvaluationError`; the caller runs this inside the
        evaluation retry loop.

        Parameters
        ----------
        pool : RetrievalPool
            The real pool to clone and leave untouched on failure.
        verdict : RetrievalVerdict
            The finalized insufficient verdict.

        Returns
        -------
        RetrievalPool
            The cloned and validated pool to use for the next round.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the decision is invalid or cannot make progress.
        """
        candidate = pool.clone()
        drops = candidate.discard(verdict.discard_specific_chunks)
        drops.extend(candidate.request(verdict.request_specific_chunks))
        if drops:
            raise RAGRetrieverEvaluationError(
                "Invalid chunk references in the decision: "
                + "; ".join(cap_errors(drops))
            )
        if verdict.call_retrievers and candidate.size() >= self.max_chunks:
            raise RAGRetrieverEvaluationError(
                "The decision leaves no capacity to consult the requested "
                f"retrievers: the pool already holds {candidate.size()} of "
                f"{self.max_chunks} chunks."
            )
        materialized = candidate.materialized_keys()
        for document_id, positions in verdict.request_specific_chunks.items():
            for position in positions:
                if (document_id, position) not in materialized:
                    raise RAGRetrieverEvaluationError(
                        "The decision requests more chunks than the maximum pool "
                        f"capacity ({self.max_chunks}); requested chunk "
                        f"{document_id}_{position} does not fit."
                    )
        if (
            candidate.size() == 0
            and not verdict.call_retrievers
            and not verdict.request_specific_chunks
        ):
            raise RAGRetrieverEvaluationError(
                "The decision leaves the pool empty and requests no retriever or chunk."
            )
        return candidate

    def _report_verdict_progress(self, verdict: RetrievalVerdict) -> None:
        """Report a verdict's optional narrative on the retrieving channel.

        The event deliberately omits ``queries``: the pipeline's own
        ``retrieving`` payload already carries the full resolved query list,
        and a retriever only knows the single query it is working on. The
        frontend renders the narrative (or a justification-only detail) without
        needing the query list.

        Parameters
        ----------
        verdict : RetrievalVerdict
            The validated verdict, possibly carrying ``message`` and/or
            ``justification``.

        Returns
        -------
        None
            Nothing is emitted when the verdict has no narrative, so the
            pipeline's own retrieving payload is left untouched.
        """
        if not verdict.message and not verdict.justification:
            return
        report_progress(
            RAG_PROGRESS_STAGE_RETRIEVING,
            message=verdict.message,
            justification=verdict.justification,
        )

    @staticmethod
    def _record_round_narrative(
        entry: Dict[str, Any],
        verdict: RetrievalVerdict,
        *,
        key_prefix: str = "",
    ) -> None:
        """Attach a verdict's optional narrative to a trace round entry.

        Parameters
        ----------
        entry : Dict[str, Any]
            The JSON-serializable round summary.
        verdict : RetrievalVerdict
            The validated verdict whose narrative is recorded.
        key_prefix : str, optional
            Prefix applied to the recorded keys. The ensemble uses
            ``"planning_"`` for its pre-round planning verdict so a later
            post-round verdict cannot overwrite it.

        Returns
        -------
        None
            ``message``/``justification`` are added only when non-empty.
        """
        if verdict.message:
            entry[f"{key_prefix}{RAG_PROGRESS_MESSAGE_KEY}"] = verdict.message
        if verdict.justification:
            entry[f"{key_prefix}{RAG_PROGRESS_JUSTIFICATION_KEY}"] = (
                verdict.justification
            )

    def _evaluate(
        self,
        query: str,
        pool: RetrievalPool,
        context: RetrievalContext,
        *,
        round_number: int,
        max_rounds: int,
        require_retriever_call: bool = False,
        apply_verdict: Callable[[RetrievalVerdict], None] | None = None,
    ) -> RetrievalVerdict:
        """Delegate the prompt rendering, model call and application to the evaluator.

        Parameters
        ----------
        query : str
            The user query under evaluation.
        pool : RetrievalPool
            The currently accumulated chunk pool.
        context : RetrievalContext
            Document and corpus knowledge for the prompt.
        round_number : int
            The 1-based evaluation round number.
        max_rounds : int
            The maximum number of evaluation rounds.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call (ensemble planning).
        apply_verdict : Callable[[RetrievalVerdict], None] | None, optional
            Transactional application callback run inside the retry loop. It must
            raise :class:`RAGRetrieverEvaluationError` for any decision that
            cannot be applied.

        Returns
        -------
        RetrievalVerdict
            The validated, finalized and successfully applied verdict.
        """
        chunks = pool.materialize()
        return self._evaluator.evaluate(
            query=query,
            chunks=chunks,
            pool_size=len(chunks),
            top_k=self.max_chunks,
            children=self.get_children(),
            context=context,
            round_number=round_number,
            max_rounds=max_rounds,
            require_retriever_call=require_retriever_call,
            apply_verdict=apply_verdict,
        )

    def _evaluate_with_pool(
        self,
        query: str,
        pool: RetrievalPool,
        context: RetrievalContext,
        *,
        round_number: int,
        max_rounds: int,
        require_retriever_call: bool = False,
    ) -> Tuple[RetrievalVerdict, RetrievalPool | None]:
        """Evaluate a round and transactionally prepare the insufficient pool.

        Parameters
        ----------
        query : str
            The user query under evaluation.
        pool : RetrievalPool
            The current real pool; it is never mutated by a failed attempt.
        context : RetrievalContext
            Document and corpus knowledge for the prompt.
        round_number : int
            The 1-based evaluation round number.
        max_rounds : int
            The maximum number of evaluation rounds.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call (ensemble planning).

        Returns
        -------
        Tuple[RetrievalVerdict, RetrievalPool | None]
            The successful verdict and the prepared clone for an insufficient
            verdict, or ``None`` for a sufficient verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the decision stays unusable after the retry budget, or an
            insufficient verdict produced no applied pool.
        """
        prepared: List[RetrievalPool] = []

        def apply(verdict: RetrievalVerdict) -> None:
            """Apply an insufficient verdict to an isolated clone."""
            if verdict.sufficient:
                return
            prepared.append(self._prepare_insufficient_verdict(pool, verdict))

        verdict = self._evaluate(
            query,
            pool,
            context,
            round_number=round_number,
            max_rounds=max_rounds,
            require_retriever_call=require_retriever_call,
            apply_verdict=apply,
        )
        if verdict.sufficient:
            return verdict, None
        if not prepared:
            raise RAGRetrieverEvaluationError(
                "An insufficient verdict did not produce an applied pool."
            )
        return verdict, prepared[0]

    @staticmethod
    def _record_verdict(entry: Dict[str, Any], verdict: RetrievalVerdict) -> None:
        """Record a finalized verdict's proposal and application state.

        Parameters
        ----------
        entry : Dict[str, Any]
            The JSON-serializable round summary.
        verdict : RetrievalVerdict
            The successfully finalized verdict.

        Returns
        -------
        None
            The action maps stay visible even for a sufficient verdict, while
            ``applied`` records that they were not applied.
        """
        entry[_ENTRY_VERDICT_KEY] = verdict.sufficient
        entry[CALL_RETRIEVERS_KEY] = dict(verdict.call_retrievers)
        entry[REQUEST_CHUNKS_KEY] = dict(verdict.request_specific_chunks)
        entry[DISCARD_KEY] = dict(verdict.discard_specific_chunks)
        entry[DROPPED_OPERATIONS_KEY] = list(verdict.dropped_operations)
        entry[_ENTRY_APPLIED_KEY] = not verdict.sufficient

    def _emit_verdict(
        self,
        entry: Dict[str, Any],
        verdict: RetrievalVerdict,
    ) -> None:
        """Report and record a finalized verdict's narrative.

        Parameters
        ----------
        entry : Dict[str, Any]
            The JSON-serializable round summary.
        verdict : RetrievalVerdict
            The successfully finalized verdict.

        Returns
        -------
        None
            Nothing is emitted when the verdict has no narrative.
        """
        self._report_verdict_progress(verdict)
        self._record_round_narrative(entry, verdict)

    def _build_trace(
        self,
        pool: List[Chunk],
        child_nodes: List[Dict[str, Any]],
        rounds: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the retriever trace node with ``children`` and ``rounds``.

        Parameters
        ----------
        pool : List[Chunk]
            The final chunk pool.
        child_nodes : List[Dict[str, Any]]
            The child trace nodes captured across all rounds.
        rounds : List[Dict[str, Any]]
            The JSON-serializable per-round summaries.

        Returns
        -------
        Dict[str, Any]
            The trace node for this retriever.
        """
        return retriever_trace(self, pool, children=child_nodes, rounds=rounds)
