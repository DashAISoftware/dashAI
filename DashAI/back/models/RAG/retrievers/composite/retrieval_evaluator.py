"""Prompt + LLM evaluation collaborator for the LLM-evaluated retrievers.

``RetrievalEvaluator`` is the single place that turns structured retrieval data
into a prompt and obtains a function-calling verdict. It performs no retrieval,
pooling or trace work and never formats chunk/document text: the prompt
component owns all rendering.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any, Callable, Dict, List, Sequence, Set, Tuple

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.retrievers.composite.evaluation_output import (
    RetrievalVerdict,
    has_actions,
    parse_evaluation_arguments,
    require_planning_calls,
    validate_call_indices,
)
from DashAI.back.models.RAG.retrievers.composite.llm_route_runner import (
    LLMRouteRunner,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.composite.structured_output import (
    cap_errors,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CALL_RETRIEVERS_KEY,
    CHUNK_DOCUMENT_ID,
    CHUNK_POSITION,
    CHUNK_TEXT,
    DISCARD_KEY,
    REQUEST_CHUNKS_KEY,
    ChunkPayload,
    RetrieverCatalog,
)

logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    """Owns the prompt, the LLM and the function-call verdict contract.

    Parameters
    ----------
    prompt : Any
        A retrieval-sufficiency prompt exposing ``format(**kwargs)``.
    llm_model : Any
        The text-to-text model used to judge the pool.
    expected_function : str
        The function name a function-calling model must call.
    function_description : str
        Human-readable description of that function.
    function_parameters : Dict[str, Any]
        JSON schema of the function's arguments.
    function_call_max_trials : int
        Maximum number of evaluation attempts, the first call included. Unusable
        verdicts are retried on the function-calling route.
    """

    def __init__(
        self,
        prompt: Any,
        llm_model: Any,
        expected_function: str,
        function_description: str,
        function_parameters: Dict[str, Any],
        function_call_max_trials: int,
    ) -> None:
        self._prompt = prompt
        self._llm_model = llm_model
        self._expected_function = expected_function
        self._function_description = function_description
        self._function_parameters = function_parameters
        self._function_call_max_trials = function_call_max_trials
        self._runner = LLMRouteRunner(
            llm_model,
            expected_function,
            function_description,
            function_parameters,
            function_call_max_trials,
            logger,
        )

    @staticmethod
    def _chunk_payload(chunks: Sequence[Chunk]) -> List[ChunkPayload]:
        """Return structured chunk payloads for the prompt.

        Parameters
        ----------
        chunks : Sequence[Chunk]
            Materialized pool chunks.

        Returns
        -------
        List[ChunkPayload]
            One payload per chunk with its document id, position and raw text.
        """
        payload: List[ChunkPayload] = []
        for chunk in chunks:
            payload.append(
                {
                    CHUNK_DOCUMENT_ID: chunk.document_id,
                    CHUNK_POSITION: chunk.document_position,
                    CHUNK_TEXT: chunk.text,
                }
            )
        return payload

    def _retriever_catalog(self, children: Sequence[Any]) -> RetrieverCatalog:
        """Return the 1-based retriever index -> schema summary mapping.

        Parameters
        ----------
        children : Sequence[Any]
            Direct child retrievers of the evaluated retriever.

        Returns
        -------
        RetrieverCatalog
            A mapping keyed by the 1-based index used by ``call_retrievers``.
        """
        catalog: RetrieverCatalog = {}
        index = 1
        for child in children:
            catalog[index] = child.get_schema_summary()
            index += 1
        return catalog

    def evaluate(
        self,
        *,
        query: str,
        chunks: Sequence[Chunk],
        pool_size: int,
        top_k: int,
        children: Sequence[Any],
        context: RetrievalContext,
        round_number: int,
        max_rounds: int,
        require_retriever_call: bool = False,
        apply_verdict: Callable[[RetrievalVerdict], None] | None = None,
    ) -> RetrievalVerdict:
        """Render the prompt and obtain the model's sufficiency verdict.

        Parameters
        ----------
        query : str
            The user query under evaluation.
        chunks : Sequence[Chunk]
            The currently materialized pool.
        pool_size : int
            Number of chunks in the materialized pool.
        top_k : int
            Maximum number of chunks the retriever may return.
        children : Sequence[Any]
            The retriever's direct children, catalogued by 1-based index.
        context : RetrievalContext
            Document and corpus knowledge for the prompt.
        round_number : int
            The 1-based evaluation round number.
        max_rounds : int
            The maximum number of evaluation rounds.
        require_retriever_call : bool, optional
            When ``True`` (ensemble planning over an empty pool), the verdict
            must be insufficient and carry at least one valid retriever call.
            The resulting error is retried on the function-calling route.
        apply_verdict : Callable[[RetrievalVerdict], None] | None, optional
            Transactional application callback run inside the retry loop. It
            receives the finalized verdict and must raise
            :class:`RAGRetrieverEvaluationError` for any decision that cannot be
            applied (invalid references, no capacity, an empty pool without a
            refill, ...). The whole model call + parse + validation + application
            is then retried.

        Returns
        -------
        RetrievalVerdict
            The validated, finalized and successfully applied verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the model does not support function calling, the output is empty,
            not a string, malformed, has no usable operation, fails finalization,
            or the application callback rejects every attempt.
        """
        prompt_text = self._prompt.format(
            input=query,
            chunks=self._chunk_payload(chunks),
            pool_size=pool_size,
            top_k=top_k,
            retrievers=self._retriever_catalog(children),
            documents=context.document_payload(),
            round_number=round_number,
            max_rounds=max_rounds,
            remaining=max(top_k - pool_size, 0),
        )
        known_keys: Set[Tuple[int, int]] = {
            (chunk.document_id, chunk.document_position) for chunk in chunks
        }

        def finalize(verdict: RetrievalVerdict) -> RetrievalVerdict:
            """Finalize and apply one parsed verdict inside the retry loop."""
            finalized = self._finalize_verdict(
                verdict,
                children,
                context,
                pool_size=pool_size,
                known_keys=known_keys,
                require_retriever_call=require_retriever_call,
            )
            if apply_verdict is not None:
                apply_verdict(finalized)
            return finalized

        def parse_call(arguments: Any) -> RetrievalVerdict:
            """Finalize and apply one function-call verdict."""
            return finalize(parse_evaluation_arguments(arguments))

        return self._runner.run(
            prompt_text,
            parse_call=parse_call,
            function_route_label="Function-calling evaluation",
        )

    @staticmethod
    def _validate_corpus_positions(
        mapping: Dict[int, List[int]],
        key: str,
        context: RetrievalContext,
        known_keys: Set[Tuple[int, int]],
        has_corpus: bool,
    ) -> Dict[int, List[int]]:
        """Reject chunk positions unknown to the corpus or the materialized pool.

        A reference is valid when it identifies a chunk already in the
        materialized pool, or when corpus knowledge exists and the chunk resolves
        from the corpus. This applies to sufficient and insufficient verdicts
        alike, so a sufficient verdict cannot reference an unknown chunk.

        Parameters
        ----------
        mapping : Dict[int, List[int]]
            Document id to chunk positions.
        key : str
            Canonical field name, echoed in error messages.
        context : RetrievalContext
            Document and corpus knowledge.
        known_keys : Set[Tuple[int, int]]
            ``(document_id, document_position)`` keys of the materialized pool.
        has_corpus : bool
            Whether ``context`` carries corpus knowledge. Computed once by the
            caller to avoid re-freezing the corpus mapping per field.

        Returns
        -------
        Dict[int, List[int]]
            A copy of the mapping when every position is known.

        Raises
        ------
        RAGRetrieverEvaluationError
            If any position is absent from both the pool and the corpus.
        """
        errors: List[str] = []
        for document_id, positions in mapping.items():
            for position in positions:
                if (document_id, position) in known_keys:
                    continue
                if has_corpus and context.get_chunk(document_id, position) is not None:
                    continue
                errors.append(
                    f"'{key}' position {position} of document {document_id} does "
                    "not exist in the retrieval pool or corpus"
                )
        if errors:
            raise RAGRetrieverEvaluationError(
                "Invalid chunk reference(s) in the decision: "
                + "; ".join(cap_errors(errors))
                + "."
            )
        return {
            document_id: list(positions) for document_id, positions in mapping.items()
        }

    def _finalize_verdict(
        self,
        verdict: RetrievalVerdict,
        children: Sequence[Any],
        context: RetrievalContext,
        *,
        pool_size: int,
        known_keys: Set[Tuple[int, int]],
        require_retriever_call: bool = False,
    ) -> RetrievalVerdict:
        """Validate a parsed verdict against the concrete retrievers and pool.

        Parameters
        ----------
        verdict : RetrievalVerdict
            The verdict produced by the parser.
        children : Sequence[Any]
            The retriever's direct children, used to validate call indices.
        context : RetrievalContext
            Document and corpus knowledge used to validate chunk positions.
        pool_size : int
            Number of chunks in the materialized pool.
        known_keys : Set[Tuple[int, int]]
            ``(document_id, document_position)`` keys of the materialized pool.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call. Used by the ensemble planning step so a chunk-only or
            sufficient planning verdict is retried instead of consuming a round.

        Returns
        -------
        RetrievalVerdict
            The verdict with ``dropped_operations`` empty, since any invalid
            operation rejects the whole verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            If a retriever index or chunk position is invalid, if a required
            retriever call is missing, if a sufficient verdict targets an empty
            pool, or if an insufficient verdict has no action.
        """
        calls = validate_call_indices(verdict.call_retrievers, len(children))
        has_corpus = bool(context.corpus())
        if not has_corpus and (
            verdict.request_specific_chunks or verdict.discard_specific_chunks
        ):
            logger.warning(
                "The retriever has no corpus knowledge; chunk references are "
                "validated against the materialized pool only."
            )
        requests = self._validate_corpus_positions(
            verdict.request_specific_chunks,
            REQUEST_CHUNKS_KEY,
            context,
            known_keys,
            has_corpus,
        )
        discards = self._validate_corpus_positions(
            verdict.discard_specific_chunks,
            DISCARD_KEY,
            context,
            known_keys,
            has_corpus,
        )
        finalized = replace(
            verdict,
            call_retrievers=calls,
            request_specific_chunks=requests,
            discard_specific_chunks=discards,
            dropped_operations=(),
        )
        if require_retriever_call:
            require_planning_calls(finalized, len(children))
        elif finalized.sufficient and pool_size == 0:
            raise RAGRetrieverEvaluationError(
                "A sufficient verdict cannot be returned over an empty pool."
            )
        if not finalized.sufficient and not has_actions(
            finalized.call_retrievers,
            finalized.request_specific_chunks,
            finalized.discard_specific_chunks,
        ):
            raise RAGRetrieverEvaluationError(
                "An insufficient verdict must perform at least one action with "
                f"at least one valid operation: '{CALL_RETRIEVERS_KEY}', "
                f"'{REQUEST_CHUNKS_KEY}' or '{DISCARD_KEY}'."
            )
        return finalized
