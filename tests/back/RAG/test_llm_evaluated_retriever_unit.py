"""Unit tests for the LLM-evaluated composite retrievers.

Instances are constructed directly (no factory) with a scripted fake LLM, fake
children and a recording prompt. These tests pin the round semantics, the
retrieval-pool request/discard rules, the strict whole-verdict failure and retry
policy, the transactional application behavior and the trace/parser shape.
"""

from __future__ import annotations

import json
import logging
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Tuple

import pytest
from pydantic import ValidationError

from DashAI.back.models.RAG.documents import Chunk, RAGDocument
from DashAI.back.models.RAG.documents.rag_document import TextSegment
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverCompositeValidationError,
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.RAG.progress_utils import progress_scope
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    MAX_FUNCTION_CALL_TRIALS,
)
from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever
from DashAI.back.models.RAG.retrievers.composite.evaluation_output import (
    CALL_RETRIEVERS_KEY,
    DISCARD_KEY,
    DROPPED_OPERATIONS_KEY,
    REQUEST_CHUNKS_KEY,
    SUFFICIENT_KEY,
    RetrievalVerdict,
    cap_dropped_operations,
    parse_evaluation_arguments,
    parse_evaluation_output,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_depth_retriever import (
    LLMEvaluatedDepthRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_ensemble_retriever import (  # noqa: E501
    LLMEvaluatedEnsembleRetriever,
)
from DashAI.back.models.RAG.retrievers.exceptions import CompositeValidationError
from DashAI.back.models.RAG.retrievers.trace_utils import retriever_trace
from DashAI.back.models.text_to_text_generation_model import (
    FunctionCallResult,
    TextToTextGenerationTaskModel,
)

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


def _chunks(count: int, document_id: int = 1) -> List[Chunk]:
    """Build ``count`` persisted-looking chunks for one document."""
    return [
        Chunk(
            id=document_id * 100 + position,
            document_id=document_id,
            document_position=position,
            text=f"chunk-{document_id}-{position}",
        )
        for position in range(count)
    ]


def _chunk_map(chunks: List[Chunk]) -> Dict[int, Dict[int, Chunk]]:
    """Group chunks into the ``{document_id: {chunk_id: Chunk}}`` mapping."""
    grouped: Dict[int, Dict[int, Chunk]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk.document_id, {})[chunk.id] = chunk
    return grouped


class _FakeChild(BaseRetriever):
    """Deterministic child retriever honouring a per-call ``top_k`` hint."""

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Expose the configured top-k path."""
        return {"top_k": "top_k"}

    def __init__(
        self,
        chunks: List[Chunk],
        top_k: int,
        default_size: Optional[int] = None,
        corpus: Optional[List[Chunk]] = None,
    ) -> None:
        """Store the returned chunks, the configured top-k and the corpus."""
        super().__init__(top_k=top_k)
        self._available = chunks
        self._top_k = top_k
        self._default_size = default_size
        self.retrieve_calls: List[Optional[int]] = []
        if corpus is not None:
            self.chunks = _chunk_map(corpus)

    def retrieve(
        self, query: str, top_k: Optional[int] = None, **kwargs: Any
    ) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Return the corpus prefix for the effective size."""
        self.retrieve_calls.append(top_k)
        effective = top_k if top_k is not None else self._default_size
        chunks = (
            list(self._available)
            if effective is None
            else list(self._available[:effective])
        )
        return chunks, retriever_trace(self, chunks)

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Return a constant distance per requested chunk."""
        return [(cid, 0.5) for cid in chunk_ids]

    @property
    def retrieval_top_k(self) -> int:
        """Return the configured top-k."""
        return self._top_k


class _ScriptedLLM(TextToTextGenerationTaskModel):
    """Fake function-calling LLM returning queued verdict arguments.

    Each queued entry becomes the ``arguments`` payload of a valid
    ``evaluate_retrieval_sufficiency`` call, so malformed-output cases can be
    scripted directly. ``calls`` records the FC messages so existing call-count
    assertions keep working.
    """

    SUPPORTS_FUNCTION_CALLING = True

    def __init__(self, outputs: List[Any]) -> None:
        """Store the queue of verdict arguments to return."""
        self._outputs = list(outputs)
        self.calls: List[Any] = []
        self.fc_calls: List[Dict[str, Any]] = []

    def generate(self, input: Any) -> List[Any]:
        """Fail: the function-calling route must be selected."""
        raise AssertionError("generate() must not be called")

    def generate_function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
    ) -> FunctionCallResult:
        """Record the call and return the next scripted arguments payload."""
        self.calls.append(messages)
        self.fc_calls.append({"messages": messages, "functions": functions})
        if not self._outputs:
            raise AssertionError("No scripted LLM output left.")
        entry = self._outputs.pop(0)
        return FunctionCallResult("evaluate_retrieval_sufficiency", entry)


class _NonFunctionCallingLLM(TextToTextGenerationTaskModel):
    """Minimal non-FC model used to assert construction rejection."""

    def __init__(self, **kwargs: Any) -> None:
        """Store an empty parameter set."""
        self.parameters: Dict[str, Any] = {}

    def generate(self, input: Any) -> List[Any]:
        """Return nothing; this model is never used for evaluation."""
        return []


class _FunctionCallingScriptedLLM(TextToTextGenerationTaskModel):
    """Fake function-calling LLM returning queued results or a configured error.

    ``generate`` deliberately fails: any accidental fall-through to the text
    route surfaces as a test failure instead of a silently tolerated call.
    """

    SUPPORTS_FUNCTION_CALLING = True

    def __init__(
        self,
        results: Optional[List[Any]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Store the queue of results and an optional error to raise."""
        self._results = list(results or [])
        self._error = error
        self.generate_calls: List[Any] = []
        self.fc_calls: List[Dict[str, Any]] = []

    def generate(self, input: Any) -> List[Any]:
        """Fail: the function-calling route must be selected instead."""
        self.generate_calls.append(input)
        raise AssertionError("generate() must not be called on the FC path")

    def generate_function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
    ) -> FunctionCallResult:
        """Record the call and return the next scripted result or error."""
        self.fc_calls.append({"messages": messages, "functions": functions})
        if self._error is not None:
            raise self._error
        if not self._results:
            raise AssertionError("No scripted function call left.")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _RecordingPrompt:
    """Fake sufficiency prompt recording its rendering arguments."""

    def __init__(self) -> None:
        """Initialise an empty call log."""
        self.calls: List[Dict[str, Any]] = []

    def format(
        self,
        input: str,
        chunks: Any,
        pool_size: Optional[int] = None,
        top_k: Optional[int] = None,
        retrievers: Any = None,
        documents: Any = None,
        round_number: Optional[int] = None,
        max_rounds: Optional[int] = None,
        remaining: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Record the structured arguments and return a stable placeholder."""
        self.calls.append(
            {
                "input": input,
                "chunks": chunks,
                "pool_size": pool_size,
                "top_k": top_k,
                "retrievers": retrievers,
                "documents": documents,
                "round_number": round_number,
                "max_rounds": max_rounds,
                "remaining": remaining,
            }
        )
        return f"EVAL pool={pool_size} catalog={retrievers}"


def _depth(
    child: _FakeChild,
    llm: TextToTextGenerationTaskModel,
    prompt: _RecordingPrompt,
    max_iters: int,
    max_chunks: int,
    function_call_max_trials: int = 1,
) -> LLMEvaluatedDepthRetriever:
    """Construct a depth retriever directly."""
    return LLMEvaluatedDepthRetriever(
        children=[child],
        max_iters=max_iters,
        max_chunks=max_chunks,
        prompt=prompt,
        llm_model=llm,
        function_call_max_trials=function_call_max_trials,
    )


def _ensemble(
    children: List[_FakeChild],
    llm: TextToTextGenerationTaskModel,
    prompt: _RecordingPrompt,
    max_iters: int,
    max_chunks: int,
    function_call_max_trials: int = 1,
) -> LLMEvaluatedEnsembleRetriever:
    """Construct an ensemble retriever directly."""
    return LLMEvaluatedEnsembleRetriever(
        children=children,
        max_iters=max_iters,
        max_chunks=max_chunks,
        prompt=prompt,
        llm_model=llm,
        function_call_max_trials=function_call_max_trials,
    )


# ---------------------------------------------------------------------------
# Retriever I — depth
# ---------------------------------------------------------------------------


def test_depth_sufficient_after_first_round():
    """A sufficient verdict in round 1 stops after one delegation and one call."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=3)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 3
    assert child.retrieve_calls == [None]
    assert len(llm.calls) == 1
    assert retriever.retrieval_top_k == 10
    assert trace["name"] == "LLMEvaluatedDepthRetriever"
    assert len(trace["children"]) == 1
    assert len(trace["rounds"]) == 1
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0]["applied"] is False
    assert trace["rounds"][0]["requested_top_k"] is None
    assert trace["rounds"][0]["returned"] == 3


def test_depth_sufficient_over_empty_pool_is_retried_then_raises():
    """A sufficient verdict is never accepted over an empty pool."""
    child = _FakeChild([], top_k=5, default_size=0)
    llm = _ScriptedLLM(['{"sufficient": true}', '{"sufficient": true}'])
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    with pytest.raises(RAGRetrieverEvaluationError, match="empty pool"):
        retriever.retrieve("q")

    assert len(llm.calls) == 2


def test_depth_sufficient_unknown_position_without_corpus_is_retried():
    """A sufficient verdict still has its chunk references validated."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": true, "request_specific_chunks": {"1": [999]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 2
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0]["applied"] is False


def test_depth_sufficient_position_in_pool_is_accepted_and_ignored():
    """A sufficient verdict may reference a chunk already in the pool."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true, "request_specific_chunks": {"1": [0]}}'])
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=1,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 1
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0][REQUEST_CHUNKS_KEY] == {1: [0]}
    assert trace["rounds"][0]["applied"] is False


def test_depth_sufficient_pool_chunk_absent_from_partial_corpus_is_accepted():
    """A pool chunk is a known reference even when the corpus omits it."""
    corpus = _chunks(5)
    child = _FakeChild(_chunks(2), top_k=5, default_size=2, corpus=[corpus[0]])
    llm = _ScriptedLLM(['{"sufficient": true, "discard_specific_chunks": {"1": [1]}}'])
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=1,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 1
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0][DISCARD_KEY] == {1: [1]}
    assert trace["rounds"][0]["applied"] is False


def test_depth_insufficient_chain_honours_call_top_k_and_stops_at_max_iters():
    """Each insufficient verdict's call_retrievers size drives the next round."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 4}}',
            '{"sufficient": false, "call_retrievers": {"1": 6}}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1, 2, 3, 4, 5]
    assert child.retrieve_calls == [None, 4, 6]
    assert len(llm.calls) == 2
    assert [entry["verdict"] for entry in trace["rounds"]] == [False, False, None]
    assert [entry["applied"] for entry in trace["rounds"][:-1]] == [True, True]
    assert "applied" not in trace["rounds"][-1]
    assert len(trace["rounds"]) == 3
    assert len(pool) <= retriever.retrieval_top_k


def test_failed_application_attempt_does_not_mutate_the_pool():
    """A rejected application attempt leaves the original pool untouched."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [999]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1]
    assert len(pool) == 2


def test_depth_insufficient_with_only_requests_consumes_an_iteration():
    """A verdict without retriever calls evaluates the updated pool next round."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2, corpus=_chunks(5))
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": true}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert child.retrieve_calls == [None]
    assert [entry["round"] for entry in trace["rounds"]] == [1, 2]
    assert trace["rounds"][1]["returned"] == 0
    assert [c.document_position for c in pool][:1] == [4]


def test_depth_progress_guarantee_bumps_zero_progress_request():
    """A request that cannot add a chunk is raised to the smallest useful size."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": false, "call_retrievers": {"1": 1}}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert child.retrieve_calls == [None, 3]
    assert len(pool) == 3
    assert trace["rounds"][1]["requested_top_k"] == 3


def test_depth_pool_dedup_and_cap():
    """The pool never exceeds max_chunks and drops duplicate chunks."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=10)
    llm = _ScriptedLLM([])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=1, max_chunks=3)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 3
    assert len({(c.document_id, c.document_position) for c in pool}) == 3


def test_depth_insufficient_without_actions_raises():
    """An insufficient verdict that performs no action fails loudly."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": false}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)

    with pytest.raises(RAGRetrieverEvaluationError, match="at least one action"):
        retriever.retrieve("q")


def test_depth_rejects_insufficient_verdict_with_empty_positions():
    """Empty position lists are not progress: the loop must fail loudly."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": false, "request_specific_chunks": {"1": []}}'])
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)

    with pytest.raises(RAGRetrieverEvaluationError, match="at least one action"):
        retriever.retrieve("q")


def test_depth_call_with_full_pool_is_retried_then_sufficient():
    """A retriever call with no free capacity is retried, not applied."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 4}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=3,
        max_chunks=2,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert child.retrieve_calls == [None]
    assert len(llm.calls) == 2
    assert len(trace["rounds"]) == 1
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][CALL_RETRIEVERS_KEY] == {}
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []
    assert len(pool) == 2


def test_depth_out_of_range_only_action_fails_after_retries():
    """An out-of-range retriever index rejects every attempt and finally raises."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"2": 3}}',
            '{"sufficient": false, "call_retrievers": {"2": 3}}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    with pytest.raises(RAGRetrieverEvaluationError, match="out of range"):
        retriever.retrieve("q")

    assert len(llm.calls) == 2


def test_depth_mixed_invalid_and_valid_call_is_retried_not_partially_applied():
    """One bad retriever index rejects the whole decision and triggers a retry."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 4, "9": 3}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=3,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 2
    assert child.retrieve_calls == [None]
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][CALL_RETRIEVERS_KEY] == {}
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_depth_discard_all_without_refill_is_retried_then_sufficient():
    """A discard-all decision with no refill is retried, not applied."""
    corpus = _chunks(5)
    child = _FakeChild(corpus[:2], top_k=5, default_size=2, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "discard_specific_chunks": {"1": [0, 1]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 2
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_depth_requires_exactly_one_child():
    """Construction rejects anything but exactly one child."""
    llm = _ScriptedLLM([])
    prompt = _RecordingPrompt()
    with pytest.raises(CompositeValidationError, match="exactly one"):
        LLMEvaluatedDepthRetriever(
            children=[_FakeChild(_chunks(3), top_k=3), _FakeChild(_chunks(3), top_k=3)],
            max_iters=2,
            max_chunks=5,
            prompt=prompt,
            llm_model=llm,
        )


def test_depth_rejects_non_function_calling_llm():
    """The depth retriever requires a function-calling model."""
    with pytest.raises(CompositeValidationError, match="function calling"):
        _depth(
            _FakeChild(_chunks(3), top_k=3),
            _NonFunctionCallingLLM(),
            _RecordingPrompt(),
            2,
            5,
        )


def test_ensemble_rejects_non_function_calling_llm():
    """The ensemble retriever requires a function-calling model."""
    with pytest.raises(CompositeValidationError, match="function calling"):
        _ensemble(
            [_FakeChild(_chunks(3), top_k=2), _FakeChild(_chunks(3), top_k=2)],
            _NonFunctionCallingLLM(),
            _RecordingPrompt(),
            2,
            5,
        )


def test_depth_prompt_receives_structured_catalog_and_documents():
    """The recording prompt receives Python lists/dicts, not rendered strings."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)
    document = RAGDocument(
        id=1,
        name="alpha",
        segments=[TextSegment(text="alpha text", page=3)],
    )
    retriever.inject_infra("path", _chunk_map(_chunks(5)), None, {1: document})

    retriever.retrieve("q")

    call = prompt.calls[0]
    assert call["chunks"] == [
        {"document_id": 1, "position": 0, "text": "chunk-1-0"},
        {"document_id": 1, "position": 1, "text": "chunk-1-1"},
    ]
    assert call["retrievers"] == {1: {"class": "_FakeChild", "params": {"top_k": 5}}}
    assert isinstance(call["documents"], list)
    assert call["documents"][0]["document_id"] == 1
    assert call["documents"][0]["name"] == "alpha"
    assert call["top_k"] == 10
    assert call["pool_size"] == 2


def test_depth_forwards_round_budget_and_remaining_to_prompt():
    """The depth retriever forwards round numbers and free slots to the prompt."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=3)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    retriever.retrieve("q")

    call = prompt.calls[0]
    assert call["round_number"] == 1
    assert call["max_rounds"] == 2
    assert call["remaining"] == 7


def test_ensemble_forwards_round_numbers_to_prompt():
    """Planning is round 1 and post-round evaluations follow with round 2."""
    child0 = _FakeChild(_chunks(10, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(10, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=3, max_chunks=10)

    retriever.retrieve("q")

    assert [call["round_number"] for call in prompt.calls] == [1, 2]
    assert all(call["max_rounds"] == 3 for call in prompt.calls)
    assert prompt.calls[0]["remaining"] == 10
    assert prompt.calls[1]["remaining"] == 8


def test_depth_max_iters_two_renders_round_one_of_one():
    """With two iterations there is a single evaluation: round 1 of 1."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)

    retriever.retrieve("q")

    assert prompt.calls[0]["round_number"] == 1
    assert prompt.calls[0]["max_rounds"] == 1


def test_ensemble_max_iters_one_renders_planning_round_one_of_one():
    """A single-round ensemble renders the planning call as round 1 of 1."""
    child0 = _FakeChild(_chunks(5), top_k=2)
    child1 = _FakeChild(_chunks(5), top_k=2)
    llm = _ScriptedLLM(['{"sufficient": false, "call_retrievers": {"1": 2}}'])
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=1, max_chunks=10)

    retriever.retrieve("q")

    assert len(prompt.calls) == 1
    assert prompt.calls[0]["round_number"] == 1
    assert prompt.calls[0]["max_rounds"] == 1


def test_depth_trace_round_includes_empty_dropped_operations():
    """Every verdict-bearing round entry carries the dropped_operations key."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)

    _, trace = retriever.retrieve("q")

    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_depth_schema_summary_is_recursive():
    """The composite summary nests its child's class and parameters."""
    retriever = _depth(
        _FakeChild(_chunks(3), top_k=3),
        _ScriptedLLM([]),
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=5,
    )

    summary = retriever.get_schema_summary()

    assert summary["class"] == "LLMEvaluatedDepthRetriever"
    assert summary["params"] == {"max_iters": 2, "max_chunks": 5}
    assert len(summary["children"]) == 1
    child_summary = summary["children"][0]
    assert child_summary["class"] == "_FakeChild"
    assert child_summary["params"] == {"top_k": 3}
    assert "children" not in child_summary
    assert json.dumps(summary)


def test_depth_request_specific_chunks_includes_unreturned_chunk():
    """An insufficient request includes a chunk no retriever returned."""
    corpus = _chunks(5)
    child = _FakeChild(corpus[:2], top_k=5, default_size=2, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=3, max_chunks=10)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [4, 0, 1]


def test_depth_unknown_chunk_position_is_rejected_and_retried():
    """One unknown chunk position rejects the whole decision and is retried."""
    corpus = _chunks(5)
    child = _FakeChild(corpus[:2], top_k=5, default_size=2, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4, 99]}}',
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=4,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert [c.document_position for c in pool] == [4, 0, 1]
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_unknown_chunk_position_without_corpus_is_rejected_and_retried(caplog):
    """Without corpus knowledge the transactional pool update rejects the chunk."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [999]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )
    with (
        caplog.at_level(
            logging.WARNING,
            logger="DashAI.back.models.RAG.retrievers.composite.retrieval_evaluator",
        ),
        caplog.at_level(
            logging.WARNING,
            logger="DashAI.back.models.RAG.retrievers.composite.llm_evaluated_retriever",
        ),
    ):
        pool, trace = retriever.retrieve("q")

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "validated against the materialized pool only" in message
        for message in messages
    )
    assert any("retrying:" in message for message in messages)
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_depth_discard_persists_across_rounds():
    """A discarded chunk stays excluded even when a later round returns it."""
    corpus = _chunks(6)
    child = _FakeChild(corpus, top_k=6, default_size=3, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 5}, '
            '"discard_specific_chunks": {"1": [1]}}',
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert sorted(c.document_position for c in pool) == [0, 2, 3, 4]
    assert trace["rounds"][0][DISCARD_KEY] == {1: [1]}


def test_depth_full_pool_discard_refills_on_next_round():
    """Discarding from a full pool lets the next request fetch a replacement."""
    corpus = _chunks(6)
    child = _FakeChild(corpus, top_k=6, default_size=5, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 6}, '
            '"discard_specific_chunks": {"1": [1]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=3, max_chunks=5)

    pool, trace = retriever.retrieve("q")

    assert child.retrieve_calls == [None, 6]
    assert trace["rounds"][1]["requested_top_k"] == 6
    assert trace["rounds"][1]["returned"] == 6
    assert len(pool) == 5
    assert all(chunk.document_position != 1 for chunk in pool)
    assert any(chunk.document_position == 5 for chunk in pool)


def test_depth_request_discard_request_across_rounds():
    """Request, discard and re-request across rounds follows the last action."""
    corpus = _chunks(5)
    child = _FakeChild(corpus, top_k=5, default_size=2, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": false, "discard_specific_chunks": {"1": [4]}, '
            '"call_retrievers": {"1": 3}}',
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=5, max_chunks=10)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [4, 0, 1, 2]


def test_depth_newest_request_batch_is_materialized():
    """Consecutive request verdicts cannot starve the newest request."""
    corpus = _chunks(6)
    child = _FakeChild(corpus, top_k=6, default_size=2, corpus=corpus)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4, 5]}}',
            '{"sufficient": false, "request_specific_chunks": {"1": [3]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=4, max_chunks=2)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [3, 4]


def test_depth_sufficient_discard_does_not_mutate_pool():
    """A sufficient verdict is terminal and ignores its discard action."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true, "discard_specific_chunks": {"1": [0]}}'])
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0][DISCARD_KEY] == {1: [0]}


def test_depth_sufficient_unknown_request_without_corpus_is_rejected():
    """A sufficient verdict may not reference an unknown chunk position."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        ['{"sufficient": true, "request_specific_chunks": {"1": [999]}}']
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=1,
    )

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="not exist in the retrieval pool or corpus",
    ):
        retriever.retrieve("q")


def test_depth_sufficient_verdict_with_bad_call_index_is_retried():
    """A sufficient verdict is still rejected when it carries an invalid index."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": true, "call_retrievers": {"7": 3}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 2
    assert [c.document_position for c in pool] == [0, 1]
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][CALL_RETRIEVERS_KEY] == {}
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_depth_trace_includes_schema_summary():
    """Trace nodes carry the recursive schema summary."""
    retriever = _depth(
        _FakeChild(_chunks(3), top_k=3, default_size=1),
        _ScriptedLLM(['{"sufficient": true}']),
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=5,
    )

    _, trace = retriever.retrieve("q")

    assert trace["schema_summary"]["class"] == "LLMEvaluatedDepthRetriever"
    assert trace["children"][0]["schema_summary"]["class"] == "_FakeChild"


# ---------------------------------------------------------------------------
# Function calling — depth
# ---------------------------------------------------------------------------


def test_depth_function_calling_sufficient_stops_after_one_delegation():
    """A sufficient FC verdict stops after one delegation using the schema."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=3)
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True})]
    )
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 3
    assert child.retrieve_calls == [None]
    assert llm.generate_calls == []
    assert len(llm.fc_calls) == 1
    assert llm.fc_calls[0]["functions"] == [
        {
            "name": "evaluate_retrieval_sufficiency",
            "description": LLMEvaluatedDepthRetriever.FUNCTION_DESCRIPTION,
            "parameters": LLMEvaluatedDepthRetriever.FUNCTION_PARAMETERS,
        }
    ]
    parameters = llm.fc_calls[0]["functions"][0]["parameters"]
    assert parameters["required"] == [SUFFICIENT_KEY]
    assert set(parameters["properties"]) == {
        SUFFICIENT_KEY,
        CALL_RETRIEVERS_KEY,
        REQUEST_CHUNKS_KEY,
        DISCARD_KEY,
        RAG_PROGRESS_MESSAGE_KEY,
        RAG_PROGRESS_JUSTIFICATION_KEY,
    }
    assert parameters["properties"][SUFFICIENT_KEY]["type"] == "boolean"
    assert parameters["properties"][CALL_RETRIEVERS_KEY]["additionalProperties"] == {
        "type": "integer",
        "minimum": 1,
    }
    assert trace["rounds"][0]["verdict"] is True


def test_depth_function_calling_insufficient_drives_next_top_k():
    """An insufficient FC verdict's call_retrievers drives the next delegation."""
    child = _FakeChild(_chunks(10), top_k=10, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {1: 4}},
            ),
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {1: 6}},
            ),
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert child.retrieve_calls == [None, 4, 6]
    assert len(pool) == 6
    assert len(llm.fc_calls) == 2
    assert llm.generate_calls == []
    assert [entry["verdict"] for entry in trace["rounds"]] == [False, False, None]


def test_depth_function_calling_resolves_json_string_arguments():
    """FC arguments emitted as a JSON-encoded string are resolved."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("evaluate_retrieval_sufficiency", '{"sufficient": true}')]
    )
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=5)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert llm.generate_calls == []


# ---------------------------------------------------------------------------
# Retriever II — ensemble
# ---------------------------------------------------------------------------


def test_ensemble_planning_chooses_children_and_catalog_rendered():
    """The planning call selects children from a rendered catalog."""
    child0 = _FakeChild(_chunks(5), top_k=2)
    child1 = _FakeChild(_chunks(5), top_k=3)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"2": 3}}',
            '{"sufficient": true}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=2, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 3
    assert child0.retrieve_calls == []
    assert child1.retrieve_calls == [3]
    assert len(llm.calls) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0]["applied"] is False
    assert trace["rounds"][0]["calls"] == [
        {"name": "_FakeChild", "requested_top_k": 3, "returned": 3}
    ]
    assert trace["children"][0]["name"] == "_FakeChild"
    catalog = prompt.calls[0]["retrievers"]
    assert isinstance(catalog, dict)
    assert catalog[1]["class"] == "_FakeChild"
    assert catalog[2]["class"] == "_FakeChild"
    assert prompt.calls[0]["pool_size"] == 0


def test_ensemble_sufficient_over_empty_pool_is_retried_then_raises():
    """A post-round sufficient verdict is never accepted over an empty pool."""
    child0 = _FakeChild([], top_k=2)
    child1 = _FakeChild([], top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    with pytest.raises(RAGRetrieverEvaluationError, match="empty pool"):
        retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert child0.retrieve_calls == [2]


def test_ensemble_invalid_planning_is_retried_with_empty_planning_drops():
    """An invalid planning verdict is retried before any child is consulted."""
    child0 = _FakeChild(_chunks(5), top_k=2)
    child1 = _FakeChild(_chunks(5), top_k=3)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2, "9": 3}}',
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    _, trace = retriever.retrieve("q")

    planning_drops = trace["rounds"][0][f"planning_{DROPPED_OPERATIONS_KEY}"]
    assert planning_drops == []
    assert child0.retrieve_calls == [2]
    assert len(llm.calls) == 3


def test_ensemble_planning_with_only_chunk_actions_is_retried():
    """A chunk-only planning verdict is retried before it can mutate the pool."""
    corpus = _chunks(5)
    child0 = _FakeChild(corpus[:2], top_k=5, corpus=corpus)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert child0.retrieve_calls == [2]
    assert [c.document_position for c in pool] == [0, 1]
    assert all(c.document_position != 4 for c in pool)
    assert trace["rounds"][0]["verdict"] is True


def test_ensemble_call_retrievers_sizes_are_explicit():
    """Each round consults the chosen children at the model-requested size."""
    child0 = _FakeChild(_chunks(10, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(10, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 3}}',
            '{"sufficient": false, "call_retrievers": {"2": 4}}',
            '{"sufficient": true}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [3]
    assert child1.retrieve_calls == [4]
    assert len(pool) == 7
    assert [entry["verdict"] for entry in trace["rounds"]] == [False, True]
    assert [entry["applied"] for entry in trace["rounds"]] == [True, False]
    assert trace["rounds"][0]["calls"][0]["requested_top_k"] == 3
    assert trace["rounds"][0]["call_retrievers"] == {2: 4}
    assert trace["rounds"][1]["calls"][0]["requested_top_k"] == 4
    assert trace["rounds"][1]["call_retrievers"] == {}


@pytest.mark.parametrize(
    "planning",
    [
        '{"sufficient": false, "call_retrievers": {"5": 2}}',
        '{"sufficient": false}',
        '{"sufficient": false, "call_retrievers": {"1": 0}}',
        '{"sufficient": true}',
        '{"sufficient": false, "discard_specific_chunks": {"1": []}}',
    ],
)
def test_ensemble_rejects_bad_planning_verdict(planning: str):
    """Invalid planning verdicts fail loudly."""
    children = [_FakeChild(_chunks(3), top_k=2), _FakeChild(_chunks(3), top_k=2)]
    llm = _ScriptedLLM([planning])
    prompt = _RecordingPrompt()
    retriever = _ensemble(children, llm, prompt, max_iters=2, max_chunks=10)

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")


def test_ensemble_pool_never_exceeds_max_chunks():
    """The ensemble pool is capped at max_chunks."""
    child0 = _FakeChild(_chunks(10), top_k=10)
    child1 = _FakeChild(_chunks(10), top_k=10)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 10, "2": 10}}',
            '{"sufficient": true}',
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=2, max_chunks=4)

    pool, _ = retriever.retrieve("q")

    assert len(pool) == 4


def test_ensemble_full_pool_discard_refills_on_next_round():
    """Discarding from a full ensemble pool lets the next call fetch a replacement."""
    corpus = _chunks(6)
    child0 = _FakeChild(corpus, top_k=6, corpus=corpus)
    child1 = _FakeChild(_chunks(2, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 5}}',
            '{"sufficient": false, "call_retrievers": {"1": 6}, '
            '"discard_specific_chunks": {"1": [1]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=3, max_chunks=5
    )

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [5, 6]
    assert child1.retrieve_calls == []
    assert len(pool) == 5
    assert all(chunk.document_position != 1 for chunk in pool)
    assert any(chunk.document_position == 5 for chunk in pool)
    assert trace["rounds"][1]["calls"][0]["requested_top_k"] == 6


def test_ensemble_round_with_only_chunk_actions_skips_consultation():
    """A verdict without retriever calls evaluates the updated pool next round."""
    corpus = _chunks(5)
    child0 = _FakeChild(corpus[:2], top_k=2, corpus=corpus)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": false, "request_specific_chunks": {"1": [4]}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=3, max_chunks=10
    )

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [2]
    assert child1.retrieve_calls == []
    assert trace["rounds"][1]["calls"] == []
    assert [c.document_position for c in pool][0] == 4


def test_ensemble_does_not_consult_when_pool_is_full():
    """The remaining budget caps consultation and stops at the pool cap."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2, "2": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=2
    )

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [2]
    assert child1.retrieve_calls == []
    assert len(trace["rounds"][0]["calls"]) == 1
    assert len(pool) == 2


def test_ensemble_duplicate_return_does_not_exhaust_budget():
    """Duplicate chunks add no budget cost, so later children are still consulted."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": false, "call_retrievers": {"1": 2, "2": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=3, max_chunks=4
    )

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [2, 2]
    assert child1.retrieve_calls == [2]
    assert len(trace["rounds"][1]["calls"]) == 2
    assert len(pool) == 4


def test_ensemble_sufficient_verdict_with_bad_call_index_is_retried():
    """A sufficient post-round verdict with an invalid index is retried."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true, "call_retrievers": {"9": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][CALL_RETRIEVERS_KEY] == {}
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_ensemble_planning_that_fills_pool_is_retried_then_valid():
    """Planning actions that fill the pool are rejected before consulting."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2, corpus=_chunks(5))
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 1}, '
            '"request_specific_chunks": {"1": [0]}}',
            '{"sufficient": false, "call_retrievers": {"1": 1}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=1,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert child0.retrieve_calls == [1]
    assert len(pool) == 1
    assert trace["rounds"][0][f"planning_{DROPPED_OPERATIONS_KEY}"] == []


def test_ensemble_planning_seven_of_seven_capacity_is_retried_then_valid():
    """The reported 7/7 planning-capacity case is retried, not surfaced."""
    corpus = _chunks(10)
    child0 = _FakeChild(corpus, top_k=7, corpus=corpus)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 1}, '
            '"request_specific_chunks": {"1": [0, 1, 2, 3, 4, 5, 6]}}',
            '{"sufficient": false, "call_retrievers": {"1": 1}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=7,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert child0.retrieve_calls == [1]
    assert len(pool) == 1
    assert trace["rounds"][0][f"planning_{DROPPED_OPERATIONS_KEY}"] == []


def test_ensemble_call_with_full_pool_is_retried_then_sufficient():
    """A post-round call with no free capacity is retried, not consulted."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=2,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(llm.calls) == 3
    assert child0.retrieve_calls == [2]
    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert trace["rounds"][0][DROPPED_OPERATIONS_KEY] == []


def test_ensemble_function_calling_planning_selects_child():
    """An FC planning verdict selects child 2 and the schema exposes the maps."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=3)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {2: 3}},
            ),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=2, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 3
    assert child0.retrieve_calls == []
    assert child1.retrieve_calls == [3]
    assert llm.generate_calls == []
    assert len(llm.fc_calls) == 2
    planning_spec = llm.fc_calls[0]["functions"][0]
    assert planning_spec["name"] == "evaluate_retrieval_sufficiency"
    assert planning_spec["description"] == (
        LLMEvaluatedEnsembleRetriever.FUNCTION_DESCRIPTION
    )
    parameters = planning_spec["parameters"]
    assert set(parameters["properties"]) == {
        SUFFICIENT_KEY,
        CALL_RETRIEVERS_KEY,
        REQUEST_CHUNKS_KEY,
        DISCARD_KEY,
        RAG_PROGRESS_MESSAGE_KEY,
        RAG_PROGRESS_JUSTIFICATION_KEY,
    }
    assert parameters["properties"][CALL_RETRIEVERS_KEY]["type"] == "object"
    assert parameters["properties"][REQUEST_CHUNKS_KEY]["type"] == "object"
    assert parameters["properties"][DISCARD_KEY]["type"] == "object"
    assert parameters["required"] == [SUFFICIENT_KEY]
    assert trace["rounds"][0]["verdict"] is True


def test_ensemble_function_calling_post_round_insufficient_selects_new_children():
    """A post-round insufficient FC verdict selects the next round's children."""
    child0 = _FakeChild(_chunks(10, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(10, document_id=2), top_k=3)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {1: 2}},
            ),
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {2: 3}},
            ),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    prompt = _RecordingPrompt()
    retriever = _ensemble([child0, child1], llm, prompt, max_iters=3, max_chunks=10)

    pool, trace = retriever.retrieve("q")

    assert child0.retrieve_calls == [2]
    assert child1.retrieve_calls == [3]
    assert len(pool) == 5
    assert llm.generate_calls == []
    assert len(llm.fc_calls) == 3
    assert [entry["verdict"] for entry in trace["rounds"]] == [False, True]


# ---------------------------------------------------------------------------
# Common behaviour
# ---------------------------------------------------------------------------


def test_both_retrievers_trace_has_children_and_rounds():
    """Both retrievers expose children and rounds in their trace node."""
    llm = _ScriptedLLM(['{"sufficient": true}'])
    prompt = _RecordingPrompt()
    depth = _depth(_FakeChild(_chunks(5), top_k=5, default_size=2), llm, prompt, 2, 5)
    _, depth_trace = depth.retrieve("q")
    assert "children" in depth_trace
    assert "rounds" in depth_trace

    llm2 = _ScriptedLLM(
        ['{"sufficient": false, "call_retrievers": {"1": 2}}', '{"sufficient": true}']
    )
    prompt2 = _RecordingPrompt()
    ensemble = _ensemble(
        [_FakeChild(_chunks(5), top_k=2), _FakeChild(_chunks(5), top_k=2)],
        llm2,
        prompt2,
        2,
        5,
    )
    _, ensemble_trace = ensemble.retrieve("q")
    assert "children" in ensemble_trace
    assert "rounds" in ensemble_trace
    assert ensemble_trace["name"] == "LLMEvaluatedEnsembleRetriever"


@pytest.mark.parametrize("bad", ["not json at all", '{"sufficient": "yes"}'])
def test_malformed_model_output_raises(bad: str):
    """A non-JSON or wrong-typed verdict fails loudly."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM([bad])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")


@pytest.mark.parametrize("bad_output", [[], [123]])
def test_non_string_or_empty_model_output_raises(bad_output: List[Any]):
    """An empty list or non-string first element fails loudly."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM([bad_output])
    prompt = _RecordingPrompt()
    retriever = _depth(child, llm, prompt, max_iters=2, max_chunks=10)

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")


# ---------------------------------------------------------------------------
# Function calling — validation and route selection
# ---------------------------------------------------------------------------


def _fc_depth(
    llm: _FunctionCallingScriptedLLM,
) -> LLMEvaluatedDepthRetriever:
    """Construct a depth retriever wired to a function-calling fake."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    return _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)


def test_function_calling_wrong_name_raises():
    """A call naming an unexpected function fails loudly with both names."""
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("some_other_function", {"sufficient": True})]
    )

    with pytest.raises(RAGRetrieverEvaluationError) as excinfo:
        _fc_depth(llm).retrieve("q")
    message = str(excinfo.value)
    assert "some_other_function" in message
    assert "evaluate_retrieval_sufficiency" in message


def test_function_calling_empty_name_raises():
    """A call with no function name fails loudly."""
    llm = _FunctionCallingScriptedLLM([FunctionCallResult("", {"sufficient": True})])

    with pytest.raises(RAGRetrieverEvaluationError, match="name"):
        _fc_depth(llm).retrieve("q")


@pytest.mark.parametrize("result", [None, {}])
def test_function_calling_unexpected_result_type_raises(result: Any):
    """A non-FunctionCallResult return value fails loudly."""
    llm = _FunctionCallingScriptedLLM([result])

    with pytest.raises(RAGRetrieverEvaluationError):
        _fc_depth(llm).retrieve("q")


def test_function_calling_invalid_arguments_type_raises():
    """A list arguments payload (neither dict nor JSON string) fails loudly."""
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("evaluate_retrieval_sufficiency", [1, 2])]
    )

    with pytest.raises(RAGRetrieverEvaluationError):
        _fc_depth(llm).retrieve("q")


@pytest.mark.parametrize(
    "arguments",
    [
        {"sufficient": "yes"},
        {"sufficient": False, "call_retrievers": {1: 0}},
        {"sufficient": False, "request_specific_chunks": {1: [-1]}},
        {"sufficient": False, "call_retrievers": {"-1": 2}},
        {
            "sufficient": False,
            "discard_specific_chunks": {1: [2]},
            "request_specific_chunks": {1: [2]},
        },
        None,
    ],
)
def test_function_calling_invalid_dict_payload_raises(arguments: Any):
    """Invalid decoded arguments payloads fail loudly."""
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("evaluate_retrieval_sufficiency", arguments)]
    )

    with pytest.raises(RAGRetrieverEvaluationError):
        _fc_depth(llm).retrieve("q")


def test_function_calling_value_error_is_wrapped():
    """A backend ValueError is wrapped mentioning function-calling failure."""
    llm = _FunctionCallingScriptedLLM(error=ValueError("bad backend value"))

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="Function calling failed",
    ) as excinfo:
        _fc_depth(llm).retrieve("q")
    assert "bad backend value" in str(excinfo.value)


def test_function_calling_type_error_propagates():
    """An unexpected TypeError from a drifted backend is not swallowed."""
    llm = _FunctionCallingScriptedLLM(error=TypeError("unexpected shape"))

    with pytest.raises(TypeError, match="unexpected shape"):
        _fc_depth(llm).retrieve("q")


def test_function_calling_missing_spec_is_actionable():
    """A subclass without a declared function spec fails with guidance."""

    class _NoSpecDepthRetriever(LLMEvaluatedDepthRetriever):
        EXPECTED_FUNCTION = ""
        FUNCTION_DESCRIPTION = ""
        FUNCTION_PARAMETERS: Dict[str, Any] = {}

    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True})]
    )
    retriever = _NoSpecDepthRetriever(
        children=[child],
        max_iters=2,
        max_chunks=10,
        prompt=_RecordingPrompt(),
        llm_model=llm,
    )

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="does not declare a function spec",
    ):
        retriever.retrieve("q")


def test_function_calling_backend_failure_is_wrapped():
    """A backend RuntimeError is wrapped mentioning function-calling failure."""
    llm = _FunctionCallingScriptedLLM(error=RuntimeError("backend exploded"))

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="Function calling failed",
    ) as excinfo:
        _fc_depth(llm).retrieve("q")
    assert "backend exploded" in str(excinfo.value)


def test_function_calling_not_implemented_is_actionable():
    """A model claiming support without an implementation fails actionably."""
    llm = _FunctionCallingScriptedLLM(error=NotImplementedError("not here"))

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="reports function calling support",
    ):
        _fc_depth(llm).retrieve("q")


def test_function_calling_not_implemented_is_not_retried():
    """A configuration error is attempted exactly once, even with trials left."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(error=NotImplementedError("not here"))
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=3,
    )

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="reports function calling support",
    ):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 1


def test_depth_retries_function_call_after_backend_error():
    """A backend failure is retried until a valid call is produced."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            RuntimeError("backend exploded"),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert len(llm.fc_calls) == 2


def test_retriever_function_call_max_trials_defaults_to_three():
    """Direct construction defaults to three and both schemas expose it."""
    child = _FakeChild(_chunks(3), top_k=3)
    depth = LLMEvaluatedDepthRetriever(
        children=[child],
        max_iters=2,
        max_chunks=5,
        prompt=_RecordingPrompt(),
        llm_model=_ScriptedLLM([]),
    )
    ensemble = LLMEvaluatedEnsembleRetriever(
        children=[child, _FakeChild(_chunks(3), top_k=3)],
        max_iters=2,
        max_chunks=5,
        prompt=_RecordingPrompt(),
        llm_model=_ScriptedLLM([]),
    )

    assert depth.function_call_max_trials == DEFAULT_FUNCTION_CALL_MAX_TRIALS == 3
    assert ensemble.function_call_max_trials == 3
    for retriever in (LLMEvaluatedDepthRetriever, LLMEvaluatedEnsembleRetriever):
        prop = retriever.get_schema()["properties"]["function_call_max_trials"]
        assert prop["placeholder"] == 3


def _retriever_schema_params(retriever: type) -> Dict[str, Any]:
    """Return a complete schema payload for a retriever, minus the trials field."""
    children = [{"component": "_FakeChild", "params": {"top_k": 3}}]
    if retriever is LLMEvaluatedEnsembleRetriever:
        children.append({"component": "_FakeChild", "params": {"top_k": 3}})
    return {
        "children": children,
        "max_chunks": 5,
        "max_iters": 2,
        "prompt": {
            "component": "DefaultRetrievalSufficiencyPrompt",
            "params": {"language": "en"},
        },
        "llm_model": {"component": "Qwen25_15BInstruct", "params": {}},
    }


@pytest.mark.parametrize(
    "retriever", [LLMEvaluatedDepthRetriever, LLMEvaluatedEnsembleRetriever]
)
def test_retriever_schema_defaults_trials_when_omitted(retriever: type):
    """A persisted config from before the parameter existed validates."""
    validated = retriever.SCHEMA.model_validate(_retriever_schema_params(retriever))

    assert validated.function_call_max_trials == DEFAULT_FUNCTION_CALL_MAX_TRIALS


@pytest.mark.parametrize(
    "retriever", [LLMEvaluatedDepthRetriever, LLMEvaluatedEnsembleRetriever]
)
@pytest.mark.parametrize(
    "value", [0, -1, None, True, "3", 3.0, MAX_FUNCTION_CALL_TRIALS + 1]
)
def test_retriever_schema_rejects_invalid_trials(retriever: type, value: Any):
    """The schema enforces the same bounds and strict type as the constructor."""
    params = _retriever_schema_params(retriever)
    params["function_call_max_trials"] = value

    with pytest.raises(ValidationError):
        retriever.SCHEMA.model_validate(params)


def test_depth_retries_function_call_after_malformed_arguments():
    """A malformed JSON arguments payload is retried until a valid call."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult("evaluate_retrieval_sufficiency", "not json"),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert len(llm.fc_calls) == 2


def test_depth_retries_function_call_when_all_operations_are_invalid():
    """An all-invalid insufficient verdict is retried and can then succeed."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {9: 3}},
            ),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, trace = retriever.retrieve("q")

    assert len(pool) == 2
    assert trace["rounds"][0]["verdict"] is True
    assert len(llm.fc_calls) == 2


def test_depth_exhausts_function_call_trials_and_raises():
    """All configured attempts are used before the last error is raised."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult("evaluate_retrieval_sufficiency", "not json"),
            FunctionCallResult("evaluate_retrieval_sufficiency", "still not json"),
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 2


def test_ensemble_retries_planning_function_call():
    """A malformed planning call is retried before consulting the children."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult("evaluate_retrieval_sufficiency", "not json"),
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": False, "call_retrievers": {1: 2}},
            ),
        ]
    )
    retriever = _ensemble(
        [child0, child1],
        llm,
        _RecordingPrompt(),
        max_iters=1,
        max_chunks=10,
        function_call_max_trials=2,
    )

    pool, _ = retriever.retrieve("q")

    assert len(pool) == 2
    assert child0.retrieve_calls == [2]
    assert len(llm.fc_calls) == 2


def test_function_calling_retry_includes_rejection_feedback():
    """The FC retry merges the previous rejection into the single user prompt."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _FunctionCallingScriptedLLM(
        [
            FunctionCallResult(
                "evaluate_retrieval_sufficiency",
                {"sufficient": "yes"},
            ),
            FunctionCallResult("evaluate_retrieval_sufficiency", {"sufficient": True}),
        ]
    )
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    retriever.retrieve("q")

    retry_messages = llm.fc_calls[1]["messages"]
    assert len(retry_messages) == 1
    assert retry_messages[0]["role"] == "user"
    assert "Your previous decision was rejected:" in retry_messages[0]["content"]
    assert "Correct it and call the function again." in retry_messages[0]["content"]


def test_retry_warning_is_truncated_to_one_short_line(caplog):
    """Retry warnings summarize the reason instead of echoing the full error."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    long_output = "not json\n" + ("x" * 1000)
    llm = _ScriptedLLM([long_output, '{"sufficient": true}'])
    retriever = _depth(
        child,
        llm,
        _RecordingPrompt(),
        max_iters=2,
        max_chunks=10,
        function_call_max_trials=2,
    )

    with caplog.at_level(
        "WARNING",
        logger="DashAI.back.models.RAG.retrievers.composite.retrieval_evaluator",
    ):
        retriever.retrieve("q")

    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name.endswith("retrieval_evaluator")
    ]
    assert warnings
    assert any("retrying:" in message for message in warnings)
    assert all("\n" not in message for message in warnings)
    assert all(len(message) < 600 for message in warnings)


@pytest.mark.parametrize("value", [0, -1, True, "3", 3.5, MAX_FUNCTION_CALL_TRIALS + 1])
def test_invalid_function_call_max_trials_rejected(value: Any):
    """Non-positive or non-integer values fail at construction."""
    child = _FakeChild(_chunks(3), top_k=3)

    with pytest.raises(
        RAGRetrieverCompositeValidationError, match="function_call_max_trials"
    ):
        LLMEvaluatedDepthRetriever(
            children=[child],
            max_iters=2,
            max_chunks=5,
            prompt=_RecordingPrompt(),
            llm_model=_ScriptedLLM([]),
            function_call_max_trials=value,
        )


def test_score_chunks_depth_delegates_and_ensemble_averages():
    """Depth delegates scoring; ensemble averages across children."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    prompt = _RecordingPrompt()
    depth = _depth(child, _ScriptedLLM([]), prompt, 2, 5)
    assert depth.score_chunks([1, 2], "q") == [(1, 0.5), (2, 0.5)]

    ensemble = _ensemble(
        [_FakeChild(_chunks(5), top_k=2), _FakeChild(_chunks(5), top_k=2)],
        _ScriptedLLM([]),
        prompt,
        2,
        5,
    )
    assert ensemble.score_chunks([1, 2], "q") == [(1, 0.5), (2, 0.5)]


def test_required_parameters_raise_when_missing():
    """Omitting max_iters/max_chunks/prompt/llm_model fails loudly."""
    child = _FakeChild(_chunks(3), top_k=3)
    base = {"children": [child], "max_iters": 2, "max_chunks": 5}
    with pytest.raises(Exception, match="max_iters"):
        LLMEvaluatedDepthRetriever(
            **{
                **base,
                "prompt": _RecordingPrompt(),
                "llm_model": _ScriptedLLM([]),
                "max_iters": None,
            }
        )
    with pytest.raises(Exception, match="prompt"):
        LLMEvaluatedDepthRetriever(
            children=[child], max_iters=2, max_chunks=5, llm_model=_ScriptedLLM([])
        )
    with pytest.raises(Exception, match="llm_model"):
        LLMEvaluatedDepthRetriever(
            children=[child], max_iters=2, max_chunks=5, prompt=_RecordingPrompt()
        )


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def test_parse_tolerates_fences_and_unknown_keys():
    """Fenced JSON with extra keys parses, unknown keys ignored."""
    verdict = parse_evaluation_output(
        '```json\n{"sufficient": false, "call_retrievers": {"1": 3}, "x": 1}\n```'
    )
    assert verdict == RetrievalVerdict(sufficient=False, call_retrievers={1: 3})


def test_parse_coerces_digit_string_keys_and_deduplicates_positions():
    """Digit-string keys become ints and repeated positions collapse."""
    verdict = parse_evaluation_output(
        '{"sufficient": true, "request_specific_chunks": {"2": [1, 1, 3]}}'
    )
    assert verdict.request_specific_chunks == {2: [1, 3]}


@pytest.mark.parametrize(
    "bad",
    [
        '{"sufficient": false, "call_retrievers": {"1": 0}}',
        '{"sufficient": false, "call_retrievers": {"0": 2}}',
        '{"sufficient": false, "call_retrievers": {"-1": 2}}',
        '{"sufficient": false, "request_specific_chunks": {"1": [-1]}}',
        '{"sufficient": false, "request_specific_chunks": {"-1": [0]}}',
        '{"sufficient": false, "call_retrievers": []}',
        '{"sufficient": false}',
        '{"sufficient": false, "discard_specific_chunks": {}}',
        '{"sufficient": false, "request_specific_chunks": {"1": []}}',
        '{"sufficient": false, "discard_specific_chunks": {"1": []}}',
    ],
)
def test_parse_rejects_invalid_action_maps(bad: str):
    """Invalid indices, positions and no-progress verdicts fail loudly."""
    with pytest.raises(RAGRetrieverEvaluationError):
        parse_evaluation_output(bad)


def test_parse_rejects_duplicate_coerced_call_key():
    """Keys that collide after coercion invalidate the whole verdict."""
    with pytest.raises(RAGRetrieverEvaluationError, match="duplicate"):
        parse_evaluation_output(
            '{"sufficient": false, "call_retrievers": {"1": 3, "01": 7}}'
        )


def test_parse_rejects_invalid_top_k_even_with_later_valid_entry():
    """An invalid top_k invalidates the whole call map."""
    with pytest.raises(RAGRetrieverEvaluationError, match="top_k"):
        parse_evaluation_output(
            '{"sufficient": false, "call_retrievers": {"1": 0, "01": 3}}'
        )


def test_cap_dropped_operations_stays_within_the_bound():
    """The retained drop list is bounded overall and the tail is summarized."""
    drops = [f"drop-{index}" for index in range(60)]

    capped = cap_dropped_operations(drops)

    assert capped[:49] == drops[:49]
    assert len(capped) == 50
    assert capped[-1] == "Dropped 11 more invalid operation(s)."


def test_cap_dropped_operations_preserves_omitted_count_when_recapped():
    """Re-capping absorbs the previous summary instead of counting it as a drop."""
    drops = [f"drop-{index}" for index in range(60)]
    first = cap_dropped_operations(drops)

    merged = cap_dropped_operations(first + ["extra-0", "extra-1"])

    assert len(merged) == 50
    assert merged[-1] == "Dropped 13 more invalid operation(s)."


def test_parse_rejects_huge_invalid_key_with_bounded_message():
    """A huge model-authored key is previewed inside a bounded error."""
    huge_key = "x" * 500
    raw = json.dumps({"sufficient": False, "call_retrievers": {huge_key: 1, "1": 2}})

    with pytest.raises(RAGRetrieverEvaluationError) as excinfo:
        parse_evaluation_output(raw)

    assert len(str(excinfo.value)) < 800


def test_parse_bounds_many_invalid_call_entries():
    """Hundreds of invalid entries keep the final error message bounded."""
    calls = {f"bad{index}": 1 for index in range(500)}
    raw = json.dumps({"sufficient": False, "call_retrievers": calls})

    with pytest.raises(RAGRetrieverEvaluationError) as excinfo:
        parse_evaluation_output(raw)

    message = str(excinfo.value)
    assert "more error(s)" in message
    assert len(message) < 8000


def test_parse_rejects_unicode_digit_mapping_key():
    """A non-ASCII digit string invalidates the verdict without a ValueError."""
    with pytest.raises(RAGRetrieverEvaluationError, match="retriever index"):
        parse_evaluation_output(
            '{"sufficient": false, "call_retrievers": {"²": 1, "1": 2}}'
        )


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (REQUEST_CHUNKS_KEY, {1: [0, 1]}),
        (DISCARD_KEY, {2: [0, 1]}),
    ],
)
def test_parse_unions_duplicate_coerced_chunk_keys(key: str, expected):
    """Duplicate coerced document ids union their positions instead of raising."""
    document_id = "1" if key == REQUEST_CHUNKS_KEY else "2"
    verdict = parse_evaluation_output(
        f'{{"sufficient": true, "{key}": '
        f'{{"{document_id}": [0], "0{document_id}": [1]}}}}'
    )

    if key == REQUEST_CHUNKS_KEY:
        mapping = verdict.request_specific_chunks
    else:
        mapping = verdict.discard_specific_chunks
    assert mapping == expected


def test_parse_rejects_conflicting_chunk_fields():
    """A chunk both requested and discarded invalidates the whole verdict."""
    with pytest.raises(RAGRetrieverEvaluationError, match="cannot be both"):
        parse_evaluation_output(
            '{"sufficient": true, "request_specific_chunks": {"1": [2, 3]}, '
            '"discard_specific_chunks": {"1": [3, 4]}}'
        )


def test_parse_rejects_one_bad_call_entry():
    """One malformed call entry invalidates the whole call map."""
    with pytest.raises(RAGRetrieverEvaluationError):
        parse_evaluation_output(
            '{"sufficient": false, "call_retrievers": '
            '{"1": 3, "not-an-index": 2, "2": 0}}'
        )


def test_parse_rejects_one_bad_request_position():
    """One malformed request position invalidates the whole chunk map."""
    with pytest.raises(RAGRetrieverEvaluationError):
        parse_evaluation_output(
            '{"sufficient": false, "request_specific_chunks": '
            '{"1": [1, "bad", true, 2]}}'
        )


def test_parse_requires_boolean_sufficient():
    """A missing or non-boolean sufficient field fails loudly."""
    with pytest.raises(RAGRetrieverEvaluationError, match="sufficient"):
        parse_evaluation_output('{"call_retrievers": {"1": 3}}')


def test_parse_arguments_accepts_dict_payload():
    """A decoded mapping is validated like a parsed text verdict."""
    verdict = parse_evaluation_arguments(
        {
            "sufficient": False,
            "call_retrievers": {"1": 4},
            "request_specific_chunks": {"2": [1]},
            "x": 2,
        }
    )
    assert verdict == RetrievalVerdict(
        sufficient=False, call_retrievers={1: 4}, request_specific_chunks={2: [1]}
    )


def test_parse_arguments_accepts_json_string_payload():
    """A JSON-encoded string payload delegates to the tolerant text parser."""
    verdict = parse_evaluation_arguments(
        '```json\n{"sufficient": true, "discard_specific_chunks": {"1": [2]}}\n```'
    )
    assert verdict == RetrievalVerdict(
        sufficient=True, discard_specific_chunks={1: [2]}
    )


def test_parse_arguments_accepts_non_dict_mapping():
    """A read-only mapping is accepted like a decoded dict."""
    verdict = parse_evaluation_arguments(MappingProxyType({"sufficient": True}))
    assert verdict == RetrievalVerdict(sufficient=True)


def test_parse_arguments_rejects_invalid_type():
    """A payload that is neither a mapping nor a string fails loudly."""
    with pytest.raises(RAGRetrieverEvaluationError, match="list"):
        parse_evaluation_arguments([1, 2])


# ---------------------------------------------------------------------------
# Narrative progress
# ---------------------------------------------------------------------------


def test_parse_accepts_narrative_fields():
    """message/justification are stripped and carried on the verdict."""
    verdict = parse_evaluation_output(
        '{"sufficient": true, "message": "  Todo listo  ", '
        '"justification": " Hay evidencia "}'
    )

    assert verdict.message == "Todo listo"
    assert verdict.justification == "Hay evidencia"


def test_parse_defaults_missing_narrative_to_empty():
    """A verdict without narrative keeps empty-string fields."""
    verdict = parse_evaluation_output('{"sufficient": true}')

    assert verdict.message == ""
    assert verdict.justification == ""


@pytest.mark.parametrize(
    "payload",
    [
        '{"sufficient": true, "message": 123}',
        '{"sufficient": true, "justification": ["x"]}',
        '{"sufficient": true, "message": null}',
        '{"sufficient": true, "justification": {"x": 1}}',
    ],
)
def test_parse_ignores_non_string_narrative(payload: str):
    """Ancillary narrative drift degrades to empty instead of failing retrieval."""
    verdict = parse_evaluation_output(payload)

    assert verdict.message == ""
    assert verdict.justification == ""


def test_parse_arguments_accepts_narrative_fields():
    """The function-calling mapping route accepts the same narrative fields."""
    verdict = parse_evaluation_arguments(
        {
            "sufficient": False,
            "call_retrievers": {1: 2},
            "message": "Buscando más información",
            "justification": "Faltan datos del diagnóstico",
        }
    )

    assert verdict.message == "Buscando más información"
    assert verdict.justification == "Faltan datos del diagnóstico"


def test_depth_emits_and_records_narrative():
    """A depth verdict's narrative reaches progress and the round trace."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": true, "message": "Descartando fragmentos", '
            '"justification": "No eran relevantes"}'
        ]
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == [
        {
            "stage": "retrieving",
            "message": "Descartando fragmentos",
            "justification": "No eran relevantes",
        }
    ]
    assert trace["rounds"][0]["message"] == "Descartando fragmentos"
    assert trace["rounds"][0]["justification"] == "No eran relevantes"


def test_depth_empty_narrative_emits_no_extra_event():
    """A verdict without narrative leaves the progress channel untouched."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(['{"sufficient": true}'])
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == []
    assert "message" not in trace["rounds"][0]
    assert "justification" not in trace["rounds"][0]


def test_ensemble_planning_emits_and_records_narrative():
    """The planning verdict's narrative is reported and stored in round one."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=3)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"2": 3}, '
            '"message": "Explorando dos fuentes", '
            '"justification": "Pueden aportar contexto"}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == [
        {
            "stage": "retrieving",
            "message": "Explorando dos fuentes",
            "justification": "Pueden aportar contexto",
        }
    ]
    assert trace["rounds"][0]["planning_message"] == "Explorando dos fuentes"
    assert trace["rounds"][0]["planning_justification"] == "Pueden aportar contexto"
    assert "message" not in trace["rounds"][0]
    assert "justification" not in trace["rounds"][0]


def test_ensemble_post_round_narrative_is_reported():
    """A post-round verdict's narrative is reported too."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true, "message": "Ya alcanza", '
            '"justification": "Hay suficiente evidencia"}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == [
        {
            "stage": "retrieving",
            "message": "Ya alcanza",
            "justification": "Hay suficiente evidencia",
        }
    ]
    assert trace["rounds"][0]["message"] == "Ya alcanza"
    assert trace["rounds"][0]["justification"] == "Hay suficiente evidencia"


def test_ensemble_invalid_planning_verdict_reports_nothing():
    """An invalid planning verdict must not emit narrative progress."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "message": "Plan inválido", '
            '"justification": "Sin recuperadores"}'
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append), pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")

    assert events == []


def test_depth_justification_only_emits_a_detail_event():
    """A justification without a message still reaches the progress channel."""
    child = _FakeChild(_chunks(5), top_k=5, default_size=2)
    llm = _ScriptedLLM(
        ['{"sufficient": true, "justification": "La evidencia alcanza"}']
    )
    retriever = _depth(child, llm, _RecordingPrompt(), max_iters=2, max_chunks=10)
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        retriever.retrieve("q")

    assert events == [
        {
            "stage": "retrieving",
            "justification": "La evidencia alcanza",
        }
    ]


def test_ensemble_empty_narrative_emits_no_extra_event():
    """An ensemble verdict without narrative leaves the channel untouched."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}}',
            '{"sufficient": true}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == []
    assert "planning_message" not in trace["rounds"][0]
    assert "message" not in trace["rounds"][0]


def test_ensemble_max_iters_one_records_planning_narrative():
    """A single-round ensemble still records the planning narrative."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}, '
            '"message": "Consultando una fuente"}'
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=1, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert events == [{"stage": "retrieving", "message": "Consultando una fuente"}]
    assert trace["rounds"][0]["planning_message"] == "Consultando una fuente"
    assert "message" not in trace["rounds"][0]


def test_ensemble_planning_and_post_round_narratives_are_both_recorded():
    """Planning and post-round narratives use separate trace keys."""
    child0 = _FakeChild(_chunks(5, document_id=1), top_k=2)
    child1 = _FakeChild(_chunks(5, document_id=2), top_k=2)
    llm = _ScriptedLLM(
        [
            '{"sufficient": false, "call_retrievers": {"1": 2}, '
            '"message": "Planificando", "justification": "Falta contexto"}',
            '{"sufficient": true, "message": "Listo", '
            '"justification": "Ya hay evidencia"}',
        ]
    )
    retriever = _ensemble(
        [child0, child1], llm, _RecordingPrompt(), max_iters=2, max_chunks=10
    )
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        _, trace = retriever.retrieve("q")

    assert [event["message"] for event in events] == ["Planificando", "Listo"]
    round_entry = trace["rounds"][0]
    assert round_entry["planning_message"] == "Planificando"
    assert round_entry["planning_justification"] == "Falta contexto"
    assert round_entry["message"] == "Listo"
    assert round_entry["justification"] == "Ya hay evidencia"


def test_function_descriptions_reject_invalid_decisions():
    """Both retrievers document strict decisions, hints and requested priority."""
    for retriever in (LLMEvaluatedDepthRetriever, LLMEvaluatedEnsembleRetriever):
        description = retriever.FUNCTION_DESCRIPTION.lower()
        assert "rejected" in description
        assert "valid" in description
        assert "capacity" in description
        assert "size hint" in description
        assert "requested chunks take priority" in description


def test_function_schemas_expose_optional_narrative():
    """Both retrievers declare message/justification as optional properties."""
    for retriever in (LLMEvaluatedDepthRetriever, LLMEvaluatedEnsembleRetriever):
        parameters = retriever.FUNCTION_PARAMETERS
        properties = parameters["properties"]
        assert properties[RAG_PROGRESS_MESSAGE_KEY]["type"] == "string"
        assert properties[RAG_PROGRESS_JUSTIFICATION_KEY]["type"] == "string"
        assert RAG_PROGRESS_MESSAGE_KEY not in parameters["required"]
        assert RAG_PROGRESS_JUSTIFICATION_KEY not in parameters["required"]
