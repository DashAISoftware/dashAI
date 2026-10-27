"""Unit tests for the LLM filter composite retriever.

Instances are constructed directly (no factory) with a scripted fake LLM, a fake
single child and a recording prompt. These tests pin the delegation contract, the
skip-LLM shortcuts, the strict selection parser, the function-calling/text
routes, the trace/progress shape and the constructor validation.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import pytest

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import (
    RAGRetrieverEvaluationError,
    RAGRetrieverMissingParameterError,
)
from DashAI.back.models.RAG.progress_utils import progress_scope
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PROGRESS_JUSTIFICATION_KEY,
    RAG_PROGRESS_MESSAGE_KEY,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_FILTER_K1,
    DEFAULT_FILTER_TOP_K,
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    MAX_FUNCTION_CALL_TRIALS,
)
from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever
from DashAI.back.models.RAG.retrievers.composite.filter_selection import (
    ChunkSelection,
    parse_filter_arguments,
    parse_filter_output,
)
from DashAI.back.models.RAG.retrievers.composite.llm_filter_retriever import (
    LLMFilterRetriever,
)
from DashAI.back.models.RAG.retrievers.exceptions import CompositeValidationError
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    SELECTED_CHUNKS_KEY,
)
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


class _FakeChild(BaseRetriever):
    """Deterministic child retriever recording its ``top_k`` hint."""

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Expose the configured top-k path."""
        return {"top_k": "top_k"}

    def __init__(
        self,
        chunks: List[Chunk],
        top_k: int = 10,
        honor_hint: bool = True,
    ) -> None:
        """Store the returned chunks and the configured top-k."""
        super().__init__(top_k=top_k)
        self._available = list(chunks)
        self._top_k = top_k
        self._honor_hint = honor_hint
        self.top_k_hints: List[Optional[int]] = []
        self.closed = 0

    def retrieve(
        self, query: str, top_k: Optional[int] = None, **kwargs: Any
    ) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Return the corpus prefix for the effective size."""
        self.top_k_hints.append(top_k)
        if self._honor_hint:
            effective = top_k if top_k is not None else self._top_k
            chunks = list(self._available[:effective])
        else:
            chunks = list(self._available)
        return chunks, retriever_trace(self, chunks)

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Return a constant distance per requested chunk."""
        return [(cid, 0.5) for cid in chunk_ids]

    @property
    def retrieval_top_k(self) -> int:
        """Return the configured top-k."""
        return self._top_k

    def close(self) -> None:
        """Record cleanup."""
        self.closed += 1


class _RecordingPrompt:
    """Fake filter prompt recording its structured rendering arguments."""

    def __init__(self) -> None:
        """Initialise an empty call log."""
        self.calls: List[Dict[str, Any]] = []

    def format(
        self,
        input: str,
        chunks: Any,
        top_k: Optional[int] = None,
        documents: Any = None,
        **kwargs: Any,
    ) -> str:
        """Record the structured arguments and return a stable placeholder."""
        self.calls.append(
            {
                "input": input,
                "chunks": chunks,
                "top_k": top_k,
                "documents": documents,
            }
        )
        return "FILTER"


class _NonFunctionCallingLLM(TextToTextGenerationTaskModel):
    """Minimal non-FC model used to assert construction rejection."""

    def __init__(self, **kwargs: Any) -> None:
        """Store an empty parameter set."""
        self.parameters: Dict[str, Any] = {}

    def generate(self, input: Any) -> List[Any]:
        """Return nothing; this model is never used for evaluation."""
        return []


class _FunctionCallingLLM(TextToTextGenerationTaskModel):
    """Fake function-calling LLM returning queued results or a configured error."""

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
        self.closed = 0

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

    def close(self) -> None:
        """Record cleanup."""
        self.closed += 1


def _selection(*indices: int, **kwargs: Any) -> FunctionCallResult:
    """Build a function-call result selecting the given candidate indices."""
    return FunctionCallResult(
        "select_best_chunks", {SELECTED_CHUNKS_KEY: list(indices), **kwargs}
    )


def _filter(
    child: _FakeChild,
    llm: TextToTextGenerationTaskModel,
    prompt: Optional[_RecordingPrompt] = None,
    *,
    k1: int = 10,
    top_k: int = 5,
    function_call_max_trials: int = 1,
) -> LLMFilterRetriever:
    """Construct a filter retriever directly."""
    return LLMFilterRetriever(
        children=[child],
        k1=k1,
        top_k=top_k,
        prompt=_RecordingPrompt() if prompt is None else prompt,
        llm_model=llm,
        function_call_max_trials=function_call_max_trials,
    )


# ---------------------------------------------------------------------------
# retrieval semantics
# ---------------------------------------------------------------------------


def test_delegates_with_k1_and_returns_selected_in_model_order():
    """The child is queried with ``k1`` and the model's order is preserved."""
    child = _FakeChild(_chunks(10))
    llm = _FunctionCallingLLM([_selection(4, 1, 3)])
    retriever = _filter(child, llm, k1=6, top_k=3)

    pool, trace = retriever.retrieve("q")

    assert child.top_k_hints == [6]
    assert [c.document_position for c in pool] == [3, 0, 2]
    assert retriever.retrieval_top_k == 3
    assert llm.generate_calls == []
    assert len(llm.fc_calls) == 1
    spec = llm.fc_calls[0]["functions"][0]
    assert spec["name"] == "select_best_chunks"
    assert trace["name"] == "LLMFilterRetriever"
    assert trace["chunks"] == ["1_3", "1_0", "1_2"]


def test_short_circuits_when_candidates_fit_top_k_without_llm():
    """No LLM call happens when the candidate count is within ``top_k``."""
    child = _FakeChild(_chunks(3))
    llm = _FunctionCallingLLM([])
    retriever = _filter(child, llm, k1=10, top_k=5)

    pool, trace = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1, 2]
    assert child.top_k_hints == [10]
    assert llm.fc_calls == []
    assert llm.generate_calls == []
    assert trace["selection"]["llm_used"] is False
    assert trace["selection"]["candidates"] == 3
    assert trace["selection"]["top_k"] == 5


def test_empty_candidates_returns_empty_and_keeps_child_trace():
    """An empty candidate set skips the LLM but keeps the child trace node."""
    child = _FakeChild([])
    llm = _FunctionCallingLLM([])
    retriever = _filter(child, llm, top_k=5)

    pool, trace = retriever.retrieve("q")

    assert pool == []
    assert llm.fc_calls == []
    assert len(trace["children"]) == 1
    assert trace["children"][0]["name"] == "_FakeChild"
    assert trace["selection"]["candidates"] == 0
    assert trace["selection"]["llm_used"] is False


def test_caps_and_dedupes_candidates_before_evaluation():
    """A child ignoring the hint is capped to ``k1`` and deduplicated."""
    duplicated = _chunks(5) + _chunks(5)
    child = _FakeChild(duplicated, honor_hint=False)
    llm = _FunctionCallingLLM([_selection(1, 2)])
    prompt = _RecordingPrompt()
    retriever = _filter(child, llm, prompt, k1=3, top_k=2)

    retriever.retrieve("q")

    assert child.top_k_hints == [3]
    assert len(prompt.calls[0]["chunks"]) == 3

    child2 = _FakeChild(_chunks(5) + _chunks(5), honor_hint=False)
    llm2 = _FunctionCallingLLM([_selection(1, 2)])
    prompt2 = _RecordingPrompt()
    retriever2 = _filter(child2, llm2, prompt2, k1=6, top_k=2)

    retriever2.retrieve("q")

    positions = [chunk["position"] for chunk in prompt2.calls[0]["chunks"]]
    assert positions == [0, 1, 2, 3, 4]


def test_prompt_receives_structured_chunks_and_documents():
    """The evaluator forwards structured payloads, not rendered text."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM([_selection(1, 2)])
    prompt = _RecordingPrompt()
    retriever = _filter(child, llm, prompt, k1=6, top_k=2)
    retriever.inject_infra("path", {}, None, {})

    retriever.retrieve("q")

    call = prompt.calls[0]
    assert call["input"] == "q"
    assert call["top_k"] == 2
    assert call["chunks"][0] == {
        "document_id": 1,
        "position": 0,
        "text": "chunk-1-0",
    }
    assert isinstance(call["documents"], list)


# ---------------------------------------------------------------------------
# selection tolerance and retries
# ---------------------------------------------------------------------------


def test_invalid_selection_is_retried_not_partially_applied():
    """Out-of-range/non-integer/boolean entries reject the whole selection."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [
            FunctionCallResult(
                "select_best_chunks",
                {SELECTED_CHUNKS_KEY: [1, 99, "x", True, 3]},
            ),
            _selection(1, 3),
        ]
    )
    retriever = _filter(child, llm, k1=6, top_k=3, function_call_max_trials=2)

    pool, trace = retriever.retrieve("q")

    assert len(llm.fc_calls) == 2
    assert [c.document_position for c in pool] == [0, 2]
    assert trace["selection"]["selected"] == [1, 3]
    assert trace["selection"]["dropped_operations"] == []


def test_all_invalid_selection_retries_then_raises():
    """An all-invalid selection is retried and finally raises."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM([_selection(99), _selection(98)])
    retriever = _filter(child, llm, k1=6, top_k=3, function_call_max_trials=2)

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 2


def test_duplicate_or_over_budget_selection_is_retried():
    """Duplicates and selections beyond top_k reject the whole selection."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM([_selection(2, 2, 4, 5), _selection(2, 4)])
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    pool, trace = retriever.retrieve("q")

    assert len(llm.fc_calls) == 2
    assert [c.document_position for c in pool] == [1, 3]
    assert trace["selection"]["selected"] == [2, 4]
    assert trace["selection"]["dropped_operations"] == []


def test_wrong_function_name_is_rejected_and_retried():
    """A call naming another function is retried on the function-calling route."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [
            FunctionCallResult("some_other_function", {SELECTED_CHUNKS_KEY: [1]}),
            _selection(1, 2),
        ]
    )
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1]
    assert len(llm.fc_calls) == 2


def test_not_implemented_function_calling_is_not_retried():
    """A model claiming FC support without implementing it is not retried."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(error=NotImplementedError("not here"))
    retriever = _filter(child, llm, k1=6, top_k=3, function_call_max_trials=3)

    with pytest.raises(
        RAGRetrieverEvaluationError,
        match="reports function calling support",
    ):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 1


def test_function_calling_json_string_arguments_are_resolved():
    """FC arguments emitted as a JSON-encoded string select the right chunks."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [FunctionCallResult("select_best_chunks", '{"selected_chunks": [2, 1]}')]
    )
    retriever = _filter(child, llm, k1=6, top_k=3)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [1, 0]
    assert len(llm.fc_calls) == 1


def test_malformed_json_string_arguments_are_retried():
    """A malformed arguments string is retried until a valid call arrives."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [
            FunctionCallResult("select_best_chunks", "{not json"),
            FunctionCallResult("select_best_chunks", '{"selected_chunks": [1, 2]}'),
        ]
    )
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    pool, _ = retriever.retrieve("q")

    assert [c.document_position for c in pool] == [0, 1]
    assert len(llm.fc_calls) == 2


def test_all_malformed_json_string_arguments_raise_after_retries():
    """All-malformed arguments strings exhaust the configured attempts."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [
            FunctionCallResult("select_best_chunks", "{not json"),
            FunctionCallResult("select_best_chunks", "still not json"),
        ]
    )
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    with pytest.raises(RAGRetrieverEvaluationError):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 2


def test_function_calling_type_error_propagates():
    """An unexpected TypeError from a drifted backend is never swallowed."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(error=TypeError("unexpected shape"))
    retriever = _filter(child, llm, k1=6, top_k=3, function_call_max_trials=3)

    with pytest.raises(TypeError, match="unexpected shape"):
        retriever.retrieve("q")

    assert len(llm.fc_calls) == 1


def test_retry_warning_uses_the_filter_evaluator_logger(caplog):
    """Retry warnings stay on the filter evaluator logger with a short reason."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM([_selection(99), _selection(1, 2)])
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    with caplog.at_level(
        logging.WARNING,
        logger="DashAI.back.models.RAG.retrievers.composite.filter_evaluator",
    ):
        retriever.retrieve("q")

    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name.endswith("filter_evaluator")
    ]
    assert warnings
    assert any("retrying:" in message for message in warnings)
    assert all("\n" not in message for message in warnings)


def test_filter_function_calling_retry_includes_rejection_feedback():
    """The filter FC retry merges the previous rejection into the user prompt."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [
            FunctionCallResult("select_best_chunks", "{not json"),
            _selection(1, 2),
        ]
    )
    retriever = _filter(child, llm, k1=6, top_k=2, function_call_max_trials=2)

    retriever.retrieve("q")

    retry_messages = llm.fc_calls[1]["messages"]
    assert len(retry_messages) == 1
    assert retry_messages[0]["role"] == "user"
    assert "Your previous decision was rejected:" in retry_messages[0]["content"]
    assert "Correct it and call the function again." in retry_messages[0]["content"]


# ---------------------------------------------------------------------------
# trace and progress
# ---------------------------------------------------------------------------


def test_trace_includes_children_and_json_serializable_selection():
    """The trace node carries the child node and a selection summary."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [_selection(1, 3, message="Top picks", justification="Best overlap")]
    )
    retriever = _filter(child, llm, k1=6, top_k=3)

    _, trace = retriever.retrieve("q")

    assert trace["children"][0]["name"] == "_FakeChild"
    selection = trace["selection"]
    assert selection["candidates"] == 6
    assert selection["top_k"] == 3
    assert selection["selected"] == [1, 3]
    assert selection["llm_used"] is True
    assert selection["message"] == "Top picks"
    assert selection["justification"] == "Best overlap"
    assert selection["dropped_operations"] == []
    assert json.dumps(selection)


def test_progress_emits_message_and_justification_when_supplied():
    """The model's narrative reaches the retrieving progress channel."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM(
        [_selection(1, 2, message="Filtrando", justification="Más relevantes")]
    )
    retriever = _filter(child, llm, k1=6, top_k=2)
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        retriever.retrieve("q")

    assert events == [
        {
            "stage": "retrieving",
            RAG_PROGRESS_MESSAGE_KEY: "Filtrando",
            RAG_PROGRESS_JUSTIFICATION_KEY: "Más relevantes",
        }
    ]


def test_empty_narrative_emits_no_progress_event():
    """A selection without narrative leaves the progress channel untouched."""
    child = _FakeChild(_chunks(6))
    llm = _FunctionCallingLLM([_selection(1, 2)])
    retriever = _filter(child, llm, k1=6, top_k=2)
    events: List[Dict[str, Any]] = []

    with progress_scope(events.append):
        retriever.retrieve("q")

    assert events == []


# ---------------------------------------------------------------------------
# constructor validation and simple delegates
# ---------------------------------------------------------------------------


def test_top_k_greater_than_k1_is_rejected():
    """``top_k`` may not exceed the candidate budget."""
    with pytest.raises(CompositeValidationError, match="top_k"):
        _filter(_FakeChild(_chunks(3)), _FunctionCallingLLM([]), k1=2, top_k=3)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("k1", 0),
        ("k1", -1),
        ("k1", True),
        ("top_k", 0),
        ("top_k", -1),
        ("top_k", True),
    ],
)
def test_non_positive_budgets_are_rejected(field: str, value: Any):
    """Zero, negative and boolean budgets fail loudly."""
    kwargs: Dict[str, Any] = {"k1": 5, "top_k": 2}
    kwargs[field] = value

    with pytest.raises(CompositeValidationError, match=field):
        LLMFilterRetriever(
            children=[_FakeChild(_chunks(3))],
            prompt=_RecordingPrompt(),
            llm_model=_FunctionCallingLLM([]),
            **kwargs,
        )


def test_exactly_one_child_is_required():
    """Construction rejects zero or multiple children."""
    prompt = _RecordingPrompt()
    llm = _FunctionCallingLLM([])
    with pytest.raises(CompositeValidationError, match="exactly one"):
        LLMFilterRetriever(children=[], k1=5, top_k=2, prompt=prompt, llm_model=llm)
    with pytest.raises(CompositeValidationError, match="exactly one"):
        LLMFilterRetriever(
            children=[_FakeChild(_chunks(3)), _FakeChild(_chunks(3))],
            k1=5,
            top_k=2,
            prompt=prompt,
            llm_model=llm,
        )


def test_add_and_remove_are_rejected():
    """The single-child invariant cannot be broken through the composite API."""
    retriever = _filter(_FakeChild(_chunks(3)), _FunctionCallingLLM([]))
    extra = _FakeChild(_chunks(3))

    with pytest.raises(CompositeValidationError, match="exactly one child"):
        retriever.add(extra)
    with pytest.raises(CompositeValidationError, match="exactly one child"):
        retriever.remove(retriever.get_children()[0])

    assert len(retriever.get_children()) == 1


def test_cleared_child_list_is_rejected_by_retrieve_and_score():
    """Direct private-list mutation is caught before any child is indexed."""
    retriever = _filter(_FakeChild(_chunks(3)), _FunctionCallingLLM([]))
    retriever._children.clear()

    with pytest.raises(CompositeValidationError, match="exactly one child"):
        retriever.retrieve("q")
    with pytest.raises(CompositeValidationError, match="exactly one child"):
        retriever.score_chunks([1], "q")


def test_required_prompt_and_llm_are_enforced():
    """Missing required values raise the dedicated missing-parameter error."""
    child = _FakeChild(_chunks(3))

    with pytest.raises(RAGRetrieverMissingParameterError, match="prompt"):
        LLMFilterRetriever(
            children=[child], k1=5, top_k=2, llm_model=_FunctionCallingLLM([])
        )
    with pytest.raises(RAGRetrieverMissingParameterError, match="llm_model"):
        LLMFilterRetriever(children=[child], k1=5, top_k=2, prompt=_RecordingPrompt())


def test_non_function_calling_llm_is_rejected():
    """The filter retriever requires a function-calling model."""
    with pytest.raises(CompositeValidationError, match="function calling"):
        _filter(_FakeChild(_chunks(3)), _NonFunctionCallingLLM())


def test_function_call_max_trials_defaults_and_rejects_invalid_values():
    """Trials default to the shared default and reject non-positive values."""
    child = _FakeChild(_chunks(3))
    retriever = LLMFilterRetriever(
        children=[child],
        k1=5,
        top_k=2,
        prompt=_RecordingPrompt(),
        llm_model=_FunctionCallingLLM([]),
    )
    assert retriever.function_call_max_trials == DEFAULT_FUNCTION_CALL_MAX_TRIALS

    for value in (0, -1, True, MAX_FUNCTION_CALL_TRIALS + 1):
        with pytest.raises(CompositeValidationError, match="function_call_max_trials"):
            LLMFilterRetriever(
                children=[child],
                k1=5,
                top_k=2,
                prompt=_RecordingPrompt(),
                llm_model=_FunctionCallingLLM([]),
                function_call_max_trials=value,
            )


def test_retrieval_top_k_score_chunks_schema_summary_and_representation():
    """The simple delegates and declarative metadata match the contract."""
    child = _FakeChild(_chunks(5))
    retriever = _filter(child, _FunctionCallingLLM([]), k1=6, top_k=2)

    assert retriever.retrieval_top_k == 2
    assert retriever.score_chunks([1, 2], "q") == [(1, 0.5), (2, 0.5)]

    summary = retriever.get_schema_summary()
    assert summary["class"] == "LLMFilterRetriever"
    assert summary["params"] == {"k1": 6, "top_k": 2}
    assert len(summary["children"]) == 1

    representation = LLMFilterRetriever.get_representation()
    for language in ("en", "es", "pt", "de", "zh"):
        template = getattr(representation, language)
        assert "{k1}" in template
        assert "{top_k}" in template
        assert "{prompt}" in template


def test_defaults_placeholders_are_exposed():
    """The schema seeds the shared filter budgets."""
    properties = LLMFilterRetriever.get_schema()["properties"]
    assert properties["k1"]["placeholder"] == DEFAULT_FILTER_K1
    assert properties["top_k"]["placeholder"] == DEFAULT_FILTER_TOP_K


def test_function_call_max_trials_description_names_the_configured_route():
    """The schema documents route retries and propagating backend exceptions."""
    description = LLMFilterRetriever.get_schema()["properties"][
        "function_call_max_trials"
    ]["description"]
    lowered = description.en.lower()

    assert "configured route" in lowered
    assert "both the function-calling and text routes" not in lowered
    assert "unexpected backend exception types propagate" in lowered
    assert description.es
    assert description.pt


def test_function_description_rejects_invalid_selections():
    """The function description tells the model invalid selections are retried."""
    description = LLMFilterRetriever.FUNCTION_DESCRIPTION.lower()

    assert "rejected" in description
    assert "unique" in description
    assert "in-range" in description
    assert "top_k" in description


def test_close_closes_llm_then_children():
    """Cleanup releases the LLM and then the child retriever."""
    child = _FakeChild(_chunks(3))
    llm = _FunctionCallingLLM([])
    retriever = _filter(child, llm)

    retriever.close()

    assert llm.closed == 1
    assert child.closed == 1


def test_close_logs_a_failing_llm_close_instead_of_raising(caplog):
    """A broken LLM close is logged and does not skip the child cleanup."""
    child = _FakeChild(_chunks(3))

    class _FailingCloseLLM(_FunctionCallingLLM):
        def close(self) -> None:
            raise RuntimeError("boom")

    retriever = _filter(child, _FailingCloseLLM([]))

    with caplog.at_level(
        logging.WARNING,
        logger="DashAI.back.models.RAG.retrievers.composite.llm_filter_retriever",
    ):
        retriever.close()

    assert child.closed == 1
    assert any("Error closing" in record.getMessage() for record in caplog.records)


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def test_parse_output_tolerates_fences_and_digit_strings():
    """Fenced JSON and digit-string indices are accepted."""
    selection = parse_filter_output(
        '```json\n{"selected_chunks": [1, "2"]}\n```',
        top_k=3,
        candidate_count=3,
    )

    assert selection == ChunkSelection(selected_indices=(1, 2))


def test_parse_output_rejects_unicode_digit_strings():
    """A non-ASCII digit string invalidates the selection."""
    with pytest.raises(RAGRetrieverEvaluationError, match="candidate indices"):
        parse_filter_output(
            '{"selected_chunks": ["²", "1", "2"]}',
            top_k=3,
            candidate_count=3,
        )


def test_parse_ignores_non_string_narrative():
    """Narrative drift degrades to empty instead of aborting the selection."""
    selection = parse_filter_arguments(
        {
            SELECTED_CHUNKS_KEY: [1],
            "message": 123,
            "justification": ["x"],
        },
        top_k=3,
        candidate_count=3,
    )

    assert selection.message == ""
    assert selection.justification == ""


@pytest.mark.parametrize(
    ("indices", "message"),
    [
        ([2, 2], "duplicate"),
        ([1, 2, 3], "top_k"),
        ([0], "candidate indices"),
        ([99], "candidate range"),
    ],
)
def test_parse_rejects_invalid_selection(indices: List[int], message: str):
    """Duplicates, over-budget, invalid and out-of-range indices reject it all."""
    with pytest.raises(RAGRetrieverEvaluationError, match=message):
        parse_filter_arguments(
            {SELECTED_CHUNKS_KEY: indices},
            top_k=2,
            candidate_count=3,
        )


def test_parse_bounds_many_invalid_entries():
    """Hundreds of invalid selections keep the final error message bounded."""
    indices = [f"bad{index}" for index in range(500)]

    with pytest.raises(RAGRetrieverEvaluationError) as excinfo:
        parse_filter_arguments(
            {SELECTED_CHUNKS_KEY: indices},
            top_k=3,
            candidate_count=3,
        )

    message = str(excinfo.value)
    assert "more error(s)" in message
    assert len(message) < 8000


def test_parse_arguments_accepts_mapping_and_preserves_order():
    """A decoded mapping is validated and the model order is preserved."""
    selection = parse_filter_arguments(
        {
            SELECTED_CHUNKS_KEY: [2, 1],
            "message": "  Ready  ",
            "justification": "  Best match  ",
        },
        top_k=3,
        candidate_count=3,
    )

    assert selection.selected_indices == (2, 1)
    assert selection.message == "Ready"
    assert selection.justification == "Best match"
    assert selection.dropped_operations == ()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"selected_chunks": [99]},
        {"selected_chunks": "nope"},
        {"selected_chunks": []},
    ],
)
def test_parse_rejects_unusable_output(payload: Any):
    """Missing fields, all-invalid indices and non-lists fail loudly."""
    with pytest.raises(RAGRetrieverEvaluationError):
        parse_filter_arguments(payload, top_k=2, candidate_count=3)
