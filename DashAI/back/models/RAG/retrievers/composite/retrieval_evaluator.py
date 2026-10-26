"""Prompt + LLM evaluation collaborator for the LLM-evaluated retrievers.

``RetrievalEvaluator`` is the single place that turns structured retrieval data
into a prompt, chooses the function-calling or text route, and parses the
verdict. It performs no retrieval, pooling or trace work and never formats
chunk/document text: the prompt component owns all rendering.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any, Callable, Dict, List, Sequence

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.retrievers.composite.evaluation_output import (
    RetrievalVerdict,
    cap_dropped_operations,
    has_actions,
    parse_evaluation_arguments,
    parse_evaluation_output,
    require_planning_calls,
    validate_call_indices,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
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
from DashAI.back.models.text_to_text_generation_model import FunctionCallResult

logger = logging.getLogger(__name__)

#: Maximum characters of an error reason echoed in a retry warning.
_MAX_RETRY_LOG_CHARS = 300


def _summarize_error(error: BaseException) -> str:
    """Return a short single-line summary of an evaluation error.

    Parameters
    ----------
    error : BaseException
        The error about to be retried.

    Returns
    -------
    str
        The first line of the error message, truncated for logs.
    """
    text = str(error).strip()
    if not text:
        return type(error).__name__
    first_line = text.splitlines()[0]
    if len(first_line) <= _MAX_RETRY_LOG_CHARS:
        return first_line
    return first_line[:_MAX_RETRY_LOG_CHARS] + "..."


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
        Maximum number of evaluation attempts, the first call included. Both the
        function-calling and the text route are retried on an unusable verdict.
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
            The resulting error is retried on both routes.

        Returns
        -------
        RetrievalVerdict
            The validated and finalized verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the model output is empty, not a string, malformed, has no usable
            operation, or the function-calling route fails validation.
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
        if self._llm_model.supports_function_calling():
            return self._call_function_calling(
                prompt_text, children, context, require_retriever_call
            )
        return self._call_text_route(
            prompt_text, children, context, require_retriever_call
        )

    def _retry(
        self,
        attempt_fn: Callable[[], RetrievalVerdict],
        route_label: str,
    ) -> RetrievalVerdict:
        """Run one evaluation route, retrying unusable verdicts.

        Parameters
        ----------
        attempt_fn : Callable[[], RetrievalVerdict]
            Performs one full attempt and returns a finalized verdict.
        route_label : str
            Human-readable route name used in retry warnings.

        Returns
        -------
        RetrievalVerdict
            The first successful verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            The last evaluation error, once all attempts are exhausted. Other
            exceptions propagate unchanged.
        """
        last_error: RAGRetrieverEvaluationError | None = None
        for attempt in range(1, self._function_call_max_trials + 1):
            try:
                return attempt_fn()
            except RAGRetrieverEvaluationError as err:
                last_error = err
                if attempt >= self._function_call_max_trials:
                    break
                logger.warning(
                    "%s attempt %d of %d failed for %s; retrying: %s",
                    route_label,
                    attempt,
                    self._function_call_max_trials,
                    type(self._llm_model).__name__,
                    _summarize_error(err),
                )
        if last_error is not None:
            raise last_error
        raise RAGRetrieverEvaluationError(
            "The evaluation did not produce a verdict and recorded no error."
        )

    def _call_function_calling(
        self,
        prompt_text: str,
        children: Sequence[Any],
        context: RetrievalContext,
        require_retriever_call: bool = False,
    ) -> RetrievalVerdict:
        """Call the model through its function-calling interface.

        Parameters
        ----------
        prompt_text : str
            The rendered evaluation prompt sent as the user message.
        children : Sequence[Any]
            The retriever's direct children, used to validate call indices.
        context : RetrievalContext
            Document and corpus knowledge used to validate chunk positions.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call (ensemble planning).

        Returns
        -------
        RetrievalVerdict
            The validated and finalized verdict carried by the call arguments.

        Raises
        ------
        RAGRetrieverEvaluationError
            If no function spec is declared, the backend fails, the model
            reports support without implementing it, or the returned call
            violates the contract. Unusable calls are retried up to
            ``function_call_max_trials`` attempts.
        """
        spec = self._function_call_spec()
        messages = [{"role": "user", "content": prompt_text}]

        def attempt() -> RetrievalVerdict:
            """Perform one function-calling evaluation attempt."""
            verdict = self._attempt_function_call(messages, spec)
            return self._finalize_verdict(
                verdict, children, context, require_retriever_call
            )

        try:
            return self._retry(attempt, "Function-calling evaluation")
        except NotImplementedError as err:
            # A model that claims function-calling support without implementing
            # it is a configuration error, not a transient malformed response:
            # never retry it.
            raise RAGRetrieverEvaluationError(
                f"{type(self._llm_model).__name__} reports function calling "
                "support but does not implement generate_function_call."
            ) from err

    def _call_text_route(
        self,
        prompt_text: str,
        children: Sequence[Any],
        context: RetrievalContext,
        require_retriever_call: bool = False,
    ) -> RetrievalVerdict:
        """Run the text route, retrying unusable verdicts.

        Parameters
        ----------
        prompt_text : str
            The rendered evaluation prompt sent as the user message.
        children : Sequence[Any]
            The retriever's direct children, used to validate call indices.
        context : RetrievalContext
            Document and corpus knowledge used to validate chunk positions.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call (ensemble planning).

        Returns
        -------
        RetrievalVerdict
            The validated and finalized verdict.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the output is empty, malformed or has no usable operation, after
            all configured attempts are exhausted.
        """

        def attempt() -> RetrievalVerdict:
            """Perform one text-route evaluation attempt."""
            output = self._llm_model.generate(
                [{"role": "user", "content": prompt_text}]
            )
            raw = self._extract_raw_output(output)
            verdict = parse_evaluation_output(raw)
            return self._finalize_verdict(
                verdict, children, context, require_retriever_call
            )

        return self._retry(attempt, "Text evaluation")

    @staticmethod
    def _validate_corpus_positions(
        mapping: Dict[int, List[int]],
        key: str,
        context: RetrievalContext,
        dropped: List[str],
        has_corpus: bool,
    ) -> Dict[int, List[int]]:
        """Drop chunk positions that do not exist in the retrieval corpus.

        Range validation is skipped entirely when the context carries no corpus
        knowledge; the pool then defensively skips unknown positions.

        Parameters
        ----------
        mapping : Dict[int, List[int]]
            Document id to chunk positions.
        key : str
            Canonical field name, echoed in drop messages.
        context : RetrievalContext
            Document and corpus knowledge.
        dropped : List[str]
            List the drop messages are appended to.
        has_corpus : bool
            Whether ``context`` carries corpus knowledge. Computed once by the
            caller to avoid re-freezing the corpus mapping per field.

        Returns
        -------
        Dict[int, List[int]]
            The mapping without unknown positions and empty document entries.
        """
        if not has_corpus:
            copied: Dict[int, List[int]] = {}
            for document_id, positions in mapping.items():
                copied[document_id] = list(positions)
            return copied
        valid: Dict[int, List[int]] = {}
        for document_id, positions in mapping.items():
            kept: List[int] = []
            for position in positions:
                if context.get_chunk(document_id, position) is None:
                    dropped.append(
                        f"Dropped '{key}' position {position} of document "
                        f"{document_id}: it does not exist in the retrieval "
                        "corpus."
                    )
                    continue
                kept.append(position)
            if kept:
                valid[document_id] = kept
        return valid

    def _finalize_verdict(
        self,
        verdict: RetrievalVerdict,
        children: Sequence[Any],
        context: RetrievalContext,
        require_retriever_call: bool = False,
    ) -> RetrievalVerdict:
        """Validate a parsed verdict against the concrete retrievers/corpus.

        Parameters
        ----------
        verdict : RetrievalVerdict
            The verdict produced by the parser.
        children : Sequence[Any]
            The retriever's direct children, used to validate call indices.
        context : RetrievalContext
            Document and corpus knowledge used to validate chunk positions.
        require_retriever_call : bool, optional
            Require an insufficient verdict with at least one valid retriever
            call. Used by the ensemble planning step so a chunk-only or
            sufficient planning verdict is retried instead of consuming a round.

        Returns
        -------
        RetrievalVerdict
            The verdict with out-of-range calls and unknown positions removed
            and the drop messages recorded.

        Raises
        ------
        RAGRetrieverEvaluationError
            If a required retriever call is missing, or the verdict is
            insufficient and no valid operation remains after finalization. A
            sufficient non-planning verdict is terminal and never raises.
        """
        new_drops: List[str] = []
        calls = validate_call_indices(verdict.call_retrievers, len(children), new_drops)
        has_corpus = bool(context.corpus())
        if (
            not has_corpus
            and not verdict.sufficient
            and (verdict.request_specific_chunks or verdict.discard_specific_chunks)
        ):
            logger.warning(
                "Chunk range validation was skipped because the retriever has no "
                "corpus knowledge; the pool will drop any unknown positions."
            )
        requests = self._validate_corpus_positions(
            verdict.request_specific_chunks,
            REQUEST_CHUNKS_KEY,
            context,
            new_drops,
            has_corpus,
        )
        discards = self._validate_corpus_positions(
            verdict.discard_specific_chunks,
            DISCARD_KEY,
            context,
            new_drops,
            has_corpus,
        )
        new_drops_count = len(new_drops)
        new_drops = cap_dropped_operations(new_drops)
        combined_drops = cap_dropped_operations(
            list(verdict.dropped_operations) + new_drops
        )
        finalized = replace(
            verdict,
            call_retrievers=calls,
            request_specific_chunks=requests,
            discard_specific_chunks=discards,
            dropped_operations=tuple(combined_drops),
        )
        if new_drops_count:
            logger.warning(
                "Dropped %d invalid evaluation operation(s) during finalization: %s",
                new_drops_count,
                "; ".join(new_drops),
            )
        if require_retriever_call:
            require_planning_calls(finalized, len(children))
        if not finalized.sufficient and not has_actions(
            finalized.call_retrievers,
            finalized.request_specific_chunks,
            finalized.discard_specific_chunks,
        ):
            raise RAGRetrieverEvaluationError(
                "An insufficient verdict has no valid operation left after "
                f"dropping invalid entries: '{CALL_RETRIEVERS_KEY}', "
                f"'{REQUEST_CHUNKS_KEY}' or '{DISCARD_KEY}'."
                + self._dropped_detail(finalized)
            )
        return finalized

    @staticmethod
    def _dropped_detail(verdict: RetrievalVerdict) -> str:
        """Return the dropped-operation suffix for an error message.

        Parameters
        ----------
        verdict : RetrievalVerdict
            The verdict whose drops are summarized.

        Returns
        -------
        str
            A leading-space sentence, or ``""`` when nothing was dropped.
        """
        if not verdict.dropped_operations:
            return ""
        return " Dropped operations: " + "; ".join(verdict.dropped_operations) + "."

    def _function_call_spec(self) -> Dict[str, Any]:
        """Return the function spec exposed to the function-calling backend.

        Returns
        -------
        Dict[str, Any]
            The ``name``/``description``/``parameters`` specification.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the evaluator declares no function spec.
        """
        if (
            not self._expected_function
            or not self._function_description
            or not self._function_parameters
        ):
            raise RAGRetrieverEvaluationError(
                "RetrievalEvaluator does not declare a function spec to use "
                "function calling; declare the expected function, its "
                "description and parameters or use a model without function "
                "calling."
            )
        return {
            "name": self._expected_function,
            "description": self._function_description,
            "parameters": self._function_parameters,
        }

    def _attempt_function_call(
        self, messages: List[Dict[str, str]], spec: Dict[str, Any]
    ) -> RetrievalVerdict:
        """Perform one function-call attempt and validate its result.

        Parameters
        ----------
        messages : List[Dict[str, str]]
            The chat messages sent verbatim on every attempt.
        spec : Dict[str, Any]
            The evaluation function specification.

        Returns
        -------
        RetrievalVerdict
            The validated verdict.

        Raises
        ------
        NotImplementedError
            If the model reports support but implements no function-calling
            method. Never retried; the caller converts it to a
            ``RAGRetrieverEvaluationError``.
        RAGRetrieverEvaluationError
            If the backend reports a malformed call or the returned call
            violates the contract.
        """
        try:
            result = self._llm_model.generate_function_call(
                messages=messages,
                functions=[spec],
            )
        except NotImplementedError:
            # NotImplementedError subclasses RuntimeError; re-raise it so the
            # caller can classify it as a non-retryable configuration error.
            raise
        except (ValueError, RuntimeError) as err:
            raise RAGRetrieverEvaluationError(
                f"Function calling failed: {err}"
            ) from err
        return self._validate_function_call_result(result)

    def _validate_function_call_result(self, result: Any) -> RetrievalVerdict:
        """Validate a function-call response and resolve its arguments.

        Parameters
        ----------
        result : Any
            Raw return value of ``generate_function_call``.

        Returns
        -------
        RetrievalVerdict
            The validated verdict with decoded arguments.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the result is not a :class:`FunctionCallResult`, has no name,
            names a different function, or carries invalid arguments.
        """
        if not isinstance(result, FunctionCallResult):
            raise RAGRetrieverEvaluationError(
                "The function-calling model returned an unexpected output shape: "
                f"{type(result).__name__}."
            )
        if not result.name:
            raise RAGRetrieverEvaluationError(
                "The function-calling model did not report a function name."
            )
        if result.name != self._expected_function:
            raise RAGRetrieverEvaluationError(
                f"The model called '{result.name}' instead of the expected "
                f"'{self._expected_function}'."
            )
        return parse_evaluation_arguments(result.arguments)

    @staticmethod
    def _extract_raw_output(output: Any) -> str:
        """Extract the first string from the model output list.

        Parameters
        ----------
        output : Any
            Value returned by ``generate``.

        Returns
        -------
        str
            The raw output string. A plain string is returned directly; a
            non-empty sequence yields its first element.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the output is empty, not a string/sequence, or its first element
            is not a string.
        """
        if isinstance(output, str):
            return output
        if not isinstance(output, (list, tuple)) or not output:
            raise RAGRetrieverEvaluationError(
                "The evaluation model returned an empty or non-sequence output."
            )
        raw = output[0]
        if not isinstance(raw, str):
            raise RAGRetrieverEvaluationError(
                f"The evaluation model output is not a string: {type(raw).__name__}."
            )
        return raw
