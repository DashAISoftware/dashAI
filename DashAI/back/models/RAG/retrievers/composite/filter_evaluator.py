"""Prompt + LLM collaborator for the LLM filter retriever.

``FilterEvaluator`` is the single place that turns structured candidate chunks
into a prompt and parses the model's function-calling selection. The shared
:class:`LLMRouteRunner` owns the function-call contract and bounded retries. It
performs no retrieval or trace work and never formats chunk/document text: the
prompt component owns all rendering.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.filter_selection import (
    ChunkSelection,
    parse_filter_arguments,
)
from DashAI.back.models.RAG.retrievers.composite.llm_route_runner import (
    LLMRouteRunner,
)
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    CHUNK_DOCUMENT_ID,
    CHUNK_POSITION,
    CHUNK_TEXT,
    ChunkPayload,
)

logger = logging.getLogger(__name__)


class FilterEvaluator:
    """Owns the filter prompt and the typed selection parsers.

    Parameters
    ----------
    prompt : Any
        A filter prompt exposing ``format(input=..., chunks=..., top_k=...,
        documents=...)``.
    llm_model : Any
        The text-to-text model used to select the best candidates.
    expected_function : str
        The function name a function-calling model must call.
    function_description : str
        Human-readable description of that function.
    function_parameters : Dict[str, Any]
        JSON schema of the function's arguments.
    function_call_max_trials : int
        Maximum number of evaluation attempts, the first call included. Unusable
        selections are retried on the function-calling route.
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
        self._runner = LLMRouteRunner(
            llm_model,
            expected_function,
            function_description,
            function_parameters,
            function_call_max_trials,
            logger,
        )

    @staticmethod
    def _chunk_payloads(chunks: Sequence[Chunk]) -> List[ChunkPayload]:
        """Return structured chunk payloads for the prompt.

        Parameters
        ----------
        chunks : Sequence[Chunk]
            The candidate chunks to select from.

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

    def evaluate(
        self,
        query: str,
        chunks: Sequence[Chunk],
        top_k: int,
        context: RetrievalContext,
    ) -> ChunkSelection:
        """Render the prompt and obtain the model's chunk selection.

        Parameters
        ----------
        query : str
            The user query under evaluation.
        chunks : Sequence[Chunk]
            The candidate chunks, numbered on display from 1.
        top_k : int
            Maximum number of chunks to select.
        context : RetrievalContext
            Document and corpus knowledge for the prompt.

        Returns
        -------
        ChunkSelection
            The validated selection.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the model does not support function calling, the call output is
            malformed, or the selection fails validation.
        """
        prompt_text = self._prompt.format(
            input=query,
            chunks=self._chunk_payloads(chunks),
            top_k=top_k,
            documents=context.document_payload(),
        )

        def parse_call(arguments: Any) -> ChunkSelection:
            """Parse one function-call selection."""
            return parse_filter_arguments(
                arguments, top_k=top_k, candidate_count=len(chunks)
            )

        return self._runner.run(
            prompt_text,
            parse_call=parse_call,
            function_route_label="Function-calling filter evaluation",
        )
