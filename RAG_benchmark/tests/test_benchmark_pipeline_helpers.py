"""Unit tests for the RAG pipeline benchmark helper functions.

Tests cover the pure helpers in
``RAG_benchmark/app/pipelines/base.py``: secret redaction, pipeline success
determination, the five-row process-output parser, the Data-document setup
requests and the incremental results writer. No network or DashAI app is
required.
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from DashAI.back.core.enums.status import DocumentStatus, RunStatus
from RAG_benchmark.app.config import BenchmarkConfig
from RAG_benchmark.app.models import PipelineRunResult, TurnRecord
from RAG_benchmark.app.pipelines.base import (
    PipelineBenchmarkRunner,
    _aggregate_stats,
    _iter_tokenizer_names,
    _parse_process_output,
    _pipeline_success,
    _redact_secrets,
    _write_failed_iteration,
    ensure_api_key_available,
    ensure_tokenizer_available,
)
from RAG_benchmark.app.pipelines.configs import PIPELINE_REGISTRY


def _make_turn(error: str | None = None) -> TurnRecord:
    """Build a minimal TurnRecord, optionally marked as failed."""
    return TurnRecord(
        turn_number=0,
        user_message="question",
        assistant_response="answer",
        retrieval_time_ms=1.0,
        transformation_time_ms=0.5,
        generation_time_ms=1.0,
        total_turn_time_ms=2.5,
        chunks_retrieved=0,
        queries=[],
        prompt_length_chars=len("question"),
        response_length_chars=len("answer"),
        error=error,
    )


def _nested_params() -> Dict[str, object]:
    """Return a nested parameter dict containing API keys."""
    return {
        "name": "Pub 1 - Medical Fitness",
        "parameters": {
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": {
                    "embedding_model": {
                        "component": "OpenAIEmbedding",
                        "params": {
                            "model_name": "text-embedding-ada-002",
                            "api_key": "sk-openai-secret",
                        },
                    }
                },
            },
            "generation_model": {
                "component": "LlamaModel",
                "params": {"API_key": "sk-other-secret"},
            },
        },
    }


def test_redact_secrets_nested_api_keys() -> None:
    """Both ``api_key`` and ``API_key`` are blanked while input is untouched."""
    params = _nested_params()
    redacted = _redact_secrets(params)

    assert (
        redacted["parameters"]["retriever_model"]["params"]["embedding_model"][
            "params"
        ]["api_key"]
        == ""
    )
    assert redacted["parameters"]["generation_model"]["params"]["API_key"] == ""
    assert redacted["name"] == "Pub 1 - Medical Fitness"

    assert (
        params["parameters"]["retriever_model"]["params"]["embedding_model"]["params"][
            "api_key"
        ]
        == "sk-openai-secret"
    )
    assert (
        params["parameters"]["generation_model"]["params"]["API_key"]
        == "sk-other-secret"
    )


def test_iter_tokenizer_names_finds_nested_chunkers() -> None:
    """Tokenizers nested in chunker refs are found once each."""
    params = {
        "chunking_model": {
            "component": "TokenChunkModel",
            "params": {"tokenizer_name": "intfloat/e5-mistral-7b-instruct"},
        },
        "nested": [
            {
                "component": "TokenChunkModel",
                "params": {"tokenizer_name": "dccuchile/bert-base-spanish-wwm-uncased"},
            }
        ],
    }

    assert sorted(set(_iter_tokenizer_names(params))) == [
        "dccuchile/bert-base-spanish-wwm-uncased",
        "intfloat/e5-mistral-7b-instruct",
    ]


def test_ensure_tokenizer_available_accepts_cached(monkeypatch) -> None:
    """A cached tokenizer is not downloaded again."""
    import transformers

    calls = []

    def fake_from_pretrained(name, **kwargs):
        calls.append({"name": name, **kwargs})
        return object()

    monkeypatch.setattr(
        transformers.AutoTokenizer, "from_pretrained", fake_from_pretrained
    )

    ensure_tokenizer_available("cached/tokenizer", download=False)

    assert calls == [
        {"name": "cached/tokenizer", "local_files_only": True},
    ]


def test_ensure_tokenizer_available_fails_without_download(monkeypatch) -> None:
    """A missing tokenizer raises under --no-download."""
    import transformers

    def fake_from_pretrained(name, **kwargs):
        raise OSError("missing")

    monkeypatch.setattr(
        transformers.AutoTokenizer, "from_pretrained", fake_from_pretrained
    )

    with pytest.raises(RuntimeError, match="--no-download"):
        ensure_tokenizer_available("missing/tokenizer", download=False)


def test_ensure_tokenizer_available_downloads_before_use(monkeypatch) -> None:
    """With downloads enabled, the missing tokenizer is fetched up front."""
    import transformers

    calls = []

    def fake_from_pretrained(name, **kwargs):
        calls.append({"name": name, **kwargs})
        if kwargs.get("local_files_only"):
            raise OSError("missing")
        return object()

    monkeypatch.setattr(
        transformers.AutoTokenizer, "from_pretrained", fake_from_pretrained
    )

    ensure_tokenizer_available("missing/tokenizer", download=True)

    assert calls == [
        {"name": "missing/tokenizer", "local_files_only": True},
        {"name": "missing/tokenizer"},
    ]


def test_api_key_preflight_accepts_the_environment(monkeypatch) -> None:
    """An empty param is fine when OPENAI_API_KEY supplies the credential."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    component = type("RemoteEmbedding", (), {"REQUIRES_API_KEY": True})

    ensure_api_key_available("RemoteEmbedding", component, {"params": {"api_key": ""}})


def test_api_key_preflight_rejects_a_missing_credential(monkeypatch) -> None:
    """With neither a param nor the environment, the pre-flight fails."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    component = type("RemoteEmbedding", (), {"REQUIRES_API_KEY": True})

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        ensure_api_key_available(
            "RemoteEmbedding", component, {"params": {"api_key": ""}}
        )


def test_pipeline_configs_do_not_embed_the_environment_secret(monkeypatch) -> None:
    """Building pub1 must not copy the live OpenAI key into the payload."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    config = PIPELINE_REGISTRY["pub1"]["config_fn"]([])

    assert "sk-test-secret" not in json.dumps(config)
    embedding = config["parameters"]["retriever_model"]["params"]["embedding_model"]
    assert embedding["component"] == "OpenAIEmbedding"
    assert embedding["params"]["api_key"] == ""


def test_pipeline_success_cases() -> None:
    """All success/failure combinations produce the expected flag and message."""
    assert _pipeline_success("boom", [_make_turn()]) == (False, "boom")

    assert _pipeline_success(None, []) == (False, "No turns were recorded.")

    failed = [_make_turn(error="err"), _make_turn(error="err")]
    assert _pipeline_success(None, failed) == (False, "All turns failed.")

    partial = [_make_turn(), _make_turn(error="err")]
    assert _pipeline_success(None, partial) == (True, "1 of 2 turns failed.")

    ok = [_make_turn(), _make_turn()]
    assert _pipeline_success(None, ok) == (True, None)


# ── Five-row process-output parser ──────────────────────────────────────


def _typed(data: Any, data_type: str) -> Dict[str, Any]:
    """Build one serialized ProcessData row."""
    return {"data": data, "data_type": data_type, "is_input": False}


def test_parse_process_output_five_row_layout() -> None:
    """Every field is read from its own ``data_type`` row, not by position."""
    timings = {
        "transformation_ms": 11.0,
        "retrieval_ms": 22.0,
        "generation_ms": 33.0,
        "total_ms": 66.0,
    }
    result = _parse_process_output(
        {
            "output": [
                _typed(json.dumps(["q1", "q2"]), "Queries"),
                _typed(json.dumps({"c1": {}, "c2": {}}), "Dict"),
                _typed(json.dumps([{"query": "q1"}]), "Trace"),
                _typed(json.dumps(timings), "Timings"),
                _typed("the answer", "str"),
            ]
        },
        99.0,
    )

    assert result.message == "the answer"
    assert result.chunks_retrieved == 2
    assert result.retrieved_chunks == {"c1": {}, "c2": {}}
    assert result.queries == ["q1", "q2"]
    assert result.trace == [{"query": "q1"}]
    assert result.transformation_time_ms == 11.0
    assert result.retrieval_time_ms == 22.0
    assert result.generation_time_ms == 33.0
    assert result.used_legacy_timings is False


def test_parse_process_output_selects_by_type_not_position() -> None:
    """A shuffled row order still resolves every field correctly."""
    result = _parse_process_output(
        {
            "output": [
                _typed("message", "str"),
                _typed(json.dumps(["only"]), "Queries"),
                _typed(json.dumps({"a": {}, "b": {}, "c": {}}), "Dict"),
            ]
        },
        50.0,
    )

    assert result.message == "message"
    assert result.chunks_retrieved == 3
    assert result.queries == ["only"]


def test_parse_process_output_message_is_last_non_empty_str() -> None:
    """The message is the last non-empty ``str`` row."""
    result = _parse_process_output(
        {
            "output": [
                _typed("first", "str"),
                _typed("", "str"),
                _typed("second", "str"),
                _typed("", "str"),
            ]
        },
        10.0,
    )
    assert result.message == "second"


def test_parse_process_output_legacy_two_row_fallback() -> None:
    """A legacy two-row payload without ``data_type`` uses position fallbacks."""
    result = _parse_process_output(
        {"output": [{"data": "answer"}, {"data": json.dumps(["a", "b"])}]},
        123.0,
    )

    assert result.message == "answer"
    assert result.chunks_retrieved == 2
    assert result.retrieved_chunks == ["a", "b"]
    assert result.queries == []
    assert result.used_legacy_timings is True
    assert result.transformation_time_ms == 0.0
    assert result.retrieval_time_ms == 0.0
    assert result.generation_time_ms == 123.0


def test_parse_process_output_missing_timings_uses_legacy(caplog) -> None:
    """Without a ``Timings`` row, generation falls back to the wall clock."""
    import logging

    with caplog.at_level(logging.WARNING):
        result = _parse_process_output(
            {
                "output": [
                    _typed(json.dumps(["q"]), "Queries"),
                    _typed(json.dumps({"c1": {}}), "Dict"),
                    _typed("answer", "str"),
                ]
            },
            77.0,
        )

    assert result.used_legacy_timings is True
    assert result.transformation_time_ms == 0.0
    assert result.retrieval_time_ms == 0.0
    assert result.generation_time_ms == 77.0
    assert any("Timings" in record.message for record in caplog.records)


def test_parse_process_output_malformed_json_tolerated() -> None:
    """Malformed JSON in any row is tolerated and treated as absent."""
    result = _parse_process_output(
        {
            "output": [
                _typed("{not json", "Queries"),
                _typed("also broken", "Dict"),
                _typed("nope", "Trace"),
                _typed("{still broken", "Timings"),
                _typed("answer", "str"),
            ]
        },
        42.0,
    )

    assert result.message == "answer"
    assert result.chunks_retrieved == 0
    assert result.retrieved_chunks == {}
    assert result.queries == []
    assert result.trace is None
    assert result.used_legacy_timings is True
    assert result.generation_time_ms == 42.0


def test_parse_process_output_counts_list_chunks() -> None:
    """A JSON list ``Dict`` payload is returned and counted."""
    result = _parse_process_output(
        {
            "output": [
                _typed(json.dumps(["x", "y"]), "Dict"),
                _typed("answer", "str"),
            ]
        },
        0.0,
    )
    assert result.chunks_retrieved == 2
    assert result.retrieved_chunks == ["x", "y"]


def test_parse_process_output_scalar_dict_json_counts_zero() -> None:
    """A scalar JSON ``Dict`` payload does not count as chunks."""
    result = _parse_process_output(
        {
            "output": [
                _typed('"abc"', "Dict"),
                _typed("answer", "str"),
            ]
        },
        0.0,
    )
    assert result.message == "answer"
    assert result.chunks_retrieved == 0
    assert result.retrieved_chunks == {}


def test_parse_process_output_empty_output() -> None:
    """An empty output list yields an empty, error-less parse."""
    result = _parse_process_output({"output": []}, 0.0)
    assert result.message == ""
    assert result.chunks_retrieved == 0
    assert result.queries == []
    assert result.used_legacy_timings is True


def test_parse_process_output_typed_missing_str_does_not_use_positional() -> None:
    """A typed payload missing the ``str`` row leaves the message empty.

    The legacy positional fallback must not fire when *any* recognized typed
    row is present, so the Queries JSON is never mistaken for the message.
    """
    result = _parse_process_output(
        {
            "output": [
                _typed(json.dumps(["q1", "q2"]), "Queries"),
                _typed(json.dumps({"c1": {}}), "Dict"),
            ]
        },
        55.0,
    )
    assert result.message == ""
    assert result.chunks_retrieved == 1
    assert result.queries == ["q1", "q2"]


def test_parse_process_output_typed_missing_dict_does_not_use_positional() -> None:
    """A typed payload missing the ``Dict`` row yields no chunks.

    The Trace list must never be counted as retrieved chunks via the legacy
    positional fallback when typed rows are present.
    """
    result = _parse_process_output(
        {
            "output": [
                _typed("the answer", "str"),
                _typed(json.dumps([{"query": "q1"}]), "Trace"),
            ]
        },
        55.0,
    )
    assert result.message == "the answer"
    assert result.chunks_retrieved == 0
    assert result.retrieved_chunks == {}
    assert result.trace == [{"query": "q1"}]


def test_parse_process_output_non_dict_payload_returns_empty() -> None:
    """A ``None``/list payload is tolerated instead of raising AttributeError."""
    for bad in (None, [], "not-a-dict", 3):
        result = _parse_process_output(bad, 12.0)  # type: ignore[arg-type]
        assert result.message == ""
        assert result.chunks_retrieved == 0
        assert result.retrieved_chunks == {}
        assert result.queries == []
        assert result.trace is None


@pytest.mark.parametrize(
    "timings",
    [
        {"transformation_ms": 1.0, "retrieval_ms": 2.0, "generation_ms": 3.0},
        {
            "transform_ms": 1.0,
            "retrieval_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 6.0,
        },
        {
            "transformation_ms": "1.0",
            "retrieval_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 6.0,
        },
        {
            "transformation_ms": float("nan"),
            "retrieval_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 6.0,
        },
        {
            "transformation_ms": float("inf"),
            "retrieval_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 6.0,
        },
        {
            "transformation_ms": True,
            "retrieval_ms": 2.0,
            "generation_ms": 3.0,
            "total_ms": 6.0,
        },
    ],
)
def test_parse_process_output_invalid_timings_falls_back(timings, caplog) -> None:
    """A Timings dict missing keys / non-finite values falls back to wall clock."""
    with caplog.at_level(logging.WARNING):
        result = _parse_process_output(
            {
                "output": [
                    _typed("answer", "str"),
                    _typed(json.dumps(timings), "Timings"),
                ]
            },
            88.0,
        )

    assert result.used_legacy_timings is True
    assert result.transformation_time_ms == 0.0
    assert result.retrieval_time_ms == 0.0
    assert result.generation_time_ms == 88.0
    assert any("Timings" in record.message for record in caplog.records)


# ── Aggregation ─────────────────────────────────────────────────────────


def test_aggregate_stats_averages_all_stage_times() -> None:
    """Averages include transformation, retrieval, generation and total."""
    turns = [
        TurnRecord(
            turn_number=0,
            user_message="q",
            assistant_response="a",
            retrieval_time_ms=10.0,
            transformation_time_ms=2.0,
            generation_time_ms=20.0,
            total_turn_time_ms=40.0,
            chunks_retrieved=1,
            prompt_length_chars=1,
            response_length_chars=1,
        ),
        TurnRecord(
            turn_number=1,
            user_message="q",
            assistant_response="a",
            retrieval_time_ms=30.0,
            transformation_time_ms=4.0,
            generation_time_ms=40.0,
            total_turn_time_ms=80.0,
            chunks_retrieved=1,
            prompt_length_chars=1,
            response_length_chars=1,
        ),
    ]

    avg_transformation, avg_retrieval, avg_generation, avg_turn = _aggregate_stats(
        turns
    )

    assert avg_transformation == 3.0
    assert avg_retrieval == 20.0
    assert avg_generation == 30.0
    assert avg_turn == 60.0


# ── HTTP request shapes ─────────────────────────────────────────────────


class _FakeResponse:
    """Minimal stand-in for a TestClient response."""

    def __init__(self, status_code: int, json_data=None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self) -> Any:
        return self._json


class _FakeClient:
    """Minimal stand-in for the HTTP client with recorded calls."""

    def __init__(self, get_responses=None, post_responses=None) -> None:
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.posted: list[tuple[str, dict]] = []
        self.gets: list[str] = []

    def post(self, url: str, **kwargs) -> _FakeResponse:
        self.posted.append((url, kwargs))
        return self.post_responses.pop(0)

    def get(self, url: str) -> _FakeResponse:
        self.gets.append(url)
        return self.get_responses.pop(0)


def _make_runner(fake_client: _FakeClient) -> PipelineBenchmarkRunner:
    """Build a runner with the given client wired in place of the app."""
    runner = PipelineBenchmarkRunner(BenchmarkConfig())
    runner._client = fake_client
    return runner


def test_create_process_posts_to_singular_job_route() -> None:
    """Process and job creation hit the correct API routes."""
    fake = _FakeClient(
        post_responses=[
            _FakeResponse(201, {"id": 7}),
            _FakeResponse(201, {"id": 1}),
        ]
    )
    runner = _make_runner(fake)

    process_id = runner._create_process(3, "hi")

    assert process_id == 7
    assert [url for url, _ in fake.posted] == [
        "/api/v1/generative-process/",
        "/api/v1/job/",
    ]
    job_kwargs = json.loads(fake.posted[1][1]["data"]["kwargs"])
    assert job_kwargs == {"generative_process_id": 7}


def test_create_process_raises_on_job_failure() -> None:
    """A non-201 job response raises RuntimeError."""
    fake = _FakeClient(
        post_responses=[
            _FakeResponse(201, {"id": 7}),
            _FakeResponse(404),
        ]
    )
    runner = _make_runner(fake)

    with pytest.raises(RuntimeError):
        runner._create_process(3, "hi")


def test_attach_documents_posts_to_session_documents_route() -> None:
    """Attaching the corpus hits the Data-documents route with the exact body."""
    fake = _FakeClient(
        post_responses=[
            _FakeResponse(200, [{"id": 1}, {"id": 2}, {"id": 3}]),
        ]
    )
    runner = _make_runner(fake)

    runner._attach_documents(5, [1, 2, 3])

    url, kwargs = fake.posted[0]
    assert url == "/api/v1/rag/sessions/5/documents"
    assert kwargs["json"] == {"document_ids": [1, 2, 3]}


def test_attach_documents_raises_on_failure() -> None:
    """A non-200 attach response raises RuntimeError."""
    fake = _FakeClient(post_responses=[_FakeResponse(409, {"detail": "bad"})])
    runner = _make_runner(fake)

    with pytest.raises(RuntimeError):
        runner._attach_documents(5, [1])


def test_ensure_documents_reuses_finished_documents() -> None:
    """A FINISHED document whose name matches is reused, not re-parsed."""
    fake = _FakeClient(
        get_responses=[
            _FakeResponse(
                200,
                [
                    {
                        "id": 11,
                        "name": "Llama-2.pdf",
                        "status": DocumentStatus.FINISHED.value,
                    },
                    {
                        "id": 12,
                        "name": "LoRA.pdf",
                        "status": DocumentStatus.FINISHED.value,
                    },
                ],
            )
        ]
    )
    runner = _make_runner(fake)

    ids = runner._ensure_documents([Path("Llama-2.pdf"), Path("LoRA.pdf")])

    assert ids == [11, 12]
    assert fake.posted == []
    assert fake.gets == ["/api/v1/documents/"]


def test_ensure_documents_creates_missing_documents(tmp_path) -> None:
    """A missing document is created, uploaded and polled to FINISHED."""
    paper = tmp_path / "Llama-2.pdf"
    paper.write_bytes(b"%PDF-1.4 fake")
    fake = _FakeClient(
        get_responses=[
            _FakeResponse(200, []),
            _FakeResponse(
                200,
                {
                    "id": 42,
                    "name": "Llama-2.pdf",
                    "status": DocumentStatus.FINISHED.value,
                },
            ),
        ],
        post_responses=[
            _FakeResponse(201, {"id": 42, "name": "Llama-2.pdf"}),
            _FakeResponse(201, {"id": "job-1"}),
        ],
    )
    runner = _make_runner(fake)

    ids = runner._ensure_documents([paper])

    assert ids == [42]
    assert fake.gets == [
        "/api/v1/documents/",
        "/api/v1/documents/42",
    ]

    create_url, create_kwargs = fake.posted[0]
    assert create_url == "/api/v1/documents/"
    assert create_kwargs["json"] == {
        "name": "Llama-2.pdf",
        "file_name": "Llama-2.pdf",
        "dataloader": "PypdfDocumentDataLoader",
        "dataloader_params": {
            "strict": True,
            "granularity": "block",
            "extract_images": False,
        },
    }

    job_url, job_kwargs = fake.posted[1]
    assert job_url == "/api/v1/job/"
    assert job_kwargs["data"]["job_type"] == "DocumentJob"
    assert json.loads(job_kwargs["data"]["kwargs"]) == {
        "document_id": 42,
        "name": "Llama-2.pdf",
    }
    assert "file" in job_kwargs["files"]
    assert job_kwargs["headers"]["filename"] == "Llama-2.pdf"


@pytest.mark.parametrize(
    "status",
    [
        DocumentStatus.NOT_STARTED.value,
        DocumentStatus.ERROR.value,
        DocumentStatus.DELIVERED.value,
        DocumentStatus.STARTED.value,
    ],
)
def test_ensure_documents_reenqueues_any_non_finished_conflict(
    tmp_path, status
) -> None:
    """A same-named non-FINISHED document is re-parsed instead of attached.

    DELIVERED/STARTED rows are stale leftovers because the benchmark runs the
    queue in test mode, so they must be re-enqueued just like NOT_STARTED and
    ERROR instead of being polled until the 30s budget expires.
    """
    paper = tmp_path / "Llama-2.pdf"
    paper.write_bytes(b"%PDF-1.4 fake")
    fake = _FakeClient(
        get_responses=[
            _FakeResponse(
                200,
                [{"id": 42, "name": "Llama-2.pdf", "status": status}],
            ),
            _FakeResponse(
                200,
                [{"id": 42, "name": "Llama-2.pdf", "status": status}],
            ),
            _FakeResponse(
                200,
                {
                    "id": 42,
                    "name": "Llama-2.pdf",
                    "status": DocumentStatus.FINISHED.value,
                },
            ),
        ],
        post_responses=[
            _FakeResponse(409, {"detail": "taken"}),
            _FakeResponse(201, {"id": "job-2"}),
        ],
    )
    runner = _make_runner(fake)

    ids = runner._ensure_documents([paper])

    assert ids == [42]
    job_url, job_kwargs = fake.posted[1]
    assert job_url == "/api/v1/job/"
    assert json.loads(job_kwargs["data"]["kwargs"])["document_id"] == 42


def test_poll_document_raises_on_error_status() -> None:
    """A document that ends in ERROR raises RuntimeError."""
    fake = _FakeClient(
        get_responses=[
            _FakeResponse(200, {"id": 42, "status": DocumentStatus.ERROR.value})
        ]
    )
    runner = _make_runner(fake)

    with pytest.raises(RuntimeError, match="ERROR"):
        runner._poll_document(42)


def test_poll_process_returns_finished() -> None:
    """A FINISHED process payload is returned as-is."""
    fake = _FakeClient(
        get_responses=[
            _FakeResponse(200, {"status": RunStatus.FINISHED.value, "output": []})
        ]
    )
    runner = _make_runner(fake)

    result = runner._poll_process(7)

    assert result == {"status": RunStatus.FINISHED.value, "output": []}
    assert fake.gets == ["/api/v1/generative-process/7"]


def test_poll_process_raises_on_error_status() -> None:
    """An ERROR process status raises RuntimeError."""
    fake = _FakeClient(
        get_responses=[_FakeResponse(200, {"status": RunStatus.ERROR.value})]
    )
    runner = _make_runner(fake)

    with pytest.raises(RuntimeError, match="ERROR"):
        runner._poll_process(7)


def test_poll_process_raises_on_404() -> None:
    """A missing process raises RuntimeError."""
    fake = _FakeClient(get_responses=[_FakeResponse(404)])
    runner = _make_runner(fake)

    with pytest.raises(RuntimeError, match="not found"):
        runner._poll_process(7)


# ── TurnRecord / PipelineRunResult ───────────────────────────────────────


def test_turn_record_defaults() -> None:
    """The new timing/query fields default so legacy constructions keep working."""
    turn = TurnRecord(
        turn_number=0,
        user_message="q",
        assistant_response="a",
        total_turn_time_ms=1.0,
        chunks_retrieved=0,
        prompt_length_chars=1,
        response_length_chars=1,
    )
    assert turn.retrieval_time_ms == 0.0
    assert turn.transformation_time_ms == 0.0
    assert turn.generation_time_ms == 0.0
    assert turn.queries == []


def test_pipeline_run_result_avg_transformation_default() -> None:
    """``avg_transformation_time_ms`` defaults to 0.0 for skipped results."""
    result = PipelineRunResult(
        pipeline_name="Pub 1",
        pipeline_config={},
        document_ids=[],
        turns=[],
        total_time_ms=0.0,
        avg_retrieval_time_ms=0.0,
        avg_generation_time_ms=0.0,
        avg_turn_time_ms=0.0,
        total_chunks_retrieved=0,
        success=False,
        skipped=True,
    )
    assert result.avg_transformation_time_ms == 0.0


# ── Writer ──────────────────────────────────────────────────────────────


def test_pipeline_results_writer_writes_incremental_files(tmp_path) -> None:
    """PipelineResultsWriter writes per-turn CSV plus configs/io keyed by id."""
    from RAG_benchmark.app.pipelines.writer import (
        TURN_CSV_COLUMNS,
        PipelineResultsWriter,
    )

    folder = tmp_path / "1 - Publication 1 - Medical Fitness"
    writer = PipelineResultsWriter(folder, "Publication 1 - Medical Fitness")

    config = {"name": "pub1", "parameters": {}}
    writer.write_config("iter0", config)

    turn = TurnRecord(
        turn_number=0,
        user_message="question",
        assistant_response="answer",
        retrieval_time_ms=1.0,
        transformation_time_ms=0.5,
        generation_time_ms=2.0,
        total_turn_time_ms=3.5,
        chunks_retrieved=1,
        queries=["rewritten question"],
        retrieved_chunks={"d0_0": {"text": "line1\nline2", "doc": "a.txt"}},
        prompt_length_chars=8,
        response_length_chars=6,
    )
    writer.append_turn(
        "iter0-turn0", "iter0", "Publication 1 - Medical Fitness", 0, turn
    )

    assert TURN_CSV_COLUMNS.index("transformation_time_ms") == (
        TURN_CSV_COLUMNS.index("retrieval_time_ms") + 1
    )
    assert "queries" in TURN_CSV_COLUMNS

    content = (folder / "results.csv").read_text(encoding="utf-8")
    lines = content.splitlines()
    assert lines[0].startswith("id,run_id,pipeline_name,iteration,turn_number")
    assert "transformation_time_ms" in lines[0]
    assert "retrieved_chunks" in lines[0]
    assert "queries" in lines[0]
    assert any("iter0-turn0" in line for line in lines[1:])
    assert all("\n" not in line for line in lines[1:])

    rows = list(csv.DictReader(content.splitlines()))
    assert rows[0]["transformation_time_ms"] == "0.50"
    assert rows[0]["queries"] == '["rewritten question"]'

    configs = json.loads((folder / "configs.json").read_text(encoding="utf-8"))
    assert configs["iter0"] == config

    io = json.loads((folder / "io.json").read_text(encoding="utf-8"))
    assert io["iter0-turn0"]["outputs"]["assistant_response"] == "answer"
    assert io["iter0-turn0"]["outputs"]["transformation_time_ms"] == 0.5
    assert io["iter0-turn0"]["outputs"]["queries"] == ["rewritten question"]
    assert io["iter0-turn0"]["inputs"]["user_message"] == "question"


def test_redact_secrets_recurse_into_lists() -> None:
    """Secrets nested inside lists are redacted without mutating input."""
    params = {
        "name": "test",
        "children": [
            {"role": "a"},
            {"api_key": "sk-secret"},
        ],
    }
    redacted = _redact_secrets(params)

    assert redacted["children"][1]["api_key"] == ""
    assert params["children"][1]["api_key"] == "sk-secret"


def test_write_failed_iteration_records_error_marker(tmp_path) -> None:
    """_write_failed_iteration persists an error marker turn on disk."""
    from RAG_benchmark.app.pipelines.writer import PipelineResultsWriter

    folder = tmp_path / "1 - Pub"
    writer = PipelineResultsWriter(folder, "Pub")

    _write_failed_iteration(writer, "iter0", "Pub", 0, "boom")

    io = json.loads((folder / "io.json").read_text(encoding="utf-8"))
    assert io["iter0-error"]["outputs"]["error"] == "boom"

    content = (folder / "results.csv").read_text(encoding="utf-8")
    assert "iter0-error" in content
    assert "boom" in content


def test_run_pipeline_failed_config_leaves_trace_on_disk(tmp_path) -> None:
    """A pipeline iteration that fails in config_fn still writes files."""
    config = BenchmarkConfig(results_dir=tmp_path)
    runner = PipelineBenchmarkRunner(config)
    runner._client = _FakeClient()
    runner._document_ids = [1]
    runner._user_simulator = None

    def _boom(doc_ids: List[int]) -> Dict[str, Any]:
        raise RuntimeError("boom config")

    results = runner.run_pipeline(
        pipeline_key="pubX",
        pipeline_name="Failing Pipe",
        config_fn=_boom,
        iterations=1,
        messages_per_conversation=2,
        pipeline_index=1,
    )

    assert len(results) == 1
    assert results[0].success is False

    folder = tmp_path / "pipelines" / "1 - Failing Pipe"
    configs = json.loads((folder / "configs.json").read_text(encoding="utf-8"))
    assert configs["iter0"] == {}

    io = json.loads((folder / "io.json").read_text(encoding="utf-8"))
    assert io["iter0-error"]["outputs"]["error"] == "boom config"

    content = (folder / "results.csv").read_text(encoding="utf-8")
    assert "iter0-error" in content
    assert "boom config" in content


def test_run_pipeline_non_dict_config_does_not_abort(tmp_path) -> None:
    """A config_fn returning None is coerced to {} instead of aborting."""
    config = BenchmarkConfig(results_dir=tmp_path)
    runner = PipelineBenchmarkRunner(config)
    runner._client = _FakeClient(
        get_responses=[
            _FakeResponse(200, {"status": RunStatus.FINISHED.value, "output": []}),
        ],
        post_responses=[
            _FakeResponse(201, {"id": 7}),
            _FakeResponse(200, [{"id": 7}]),
            _FakeResponse(201, {"id": 7}),
            _FakeResponse(201, {"id": 1}),
        ],
    )
    runner._document_ids = [1]
    runner._user_simulator = None

    results = runner.run_pipeline(
        pipeline_key="pubX",
        pipeline_name="None Pipe",
        config_fn=lambda doc_ids: None,
        iterations=1,
        messages_per_conversation=1,
        pipeline_index=1,
    )

    assert len(results) == 1

    folder = tmp_path / "pipelines" / "1 - None Pipe"
    configs = json.loads((folder / "configs.json").read_text(encoding="utf-8"))
    assert configs["iter0"] == {}


def test_run_pipeline_attaches_documents_to_session(tmp_path) -> None:
    """The session is created without documents, then the corpus is attached."""
    config = BenchmarkConfig(results_dir=tmp_path)
    runner = PipelineBenchmarkRunner(config)
    fake = _FakeClient(
        post_responses=[
            _FakeResponse(201, {"id": 7}),
            _FakeResponse(200, [{"id": 10}, {"id": 20}, {"id": 30}]),
        ]
    )
    runner._client = fake
    runner._document_ids = [10, 20, 30]
    runner._user_simulator = None

    captured: List[List[int]] = []

    def config_fn(doc_ids: List[int]) -> Dict[str, Any]:
        captured.append(list(doc_ids))
        return {
            "model_name": "RAGPipeline",
            "task_name": "RAGTask",
            "name": "test",
            "parameters": {"chunking_model": {}, "retriever_model": {}},
        }

    results = runner.run_pipeline(
        pipeline_key="pubX",
        pipeline_name="Test",
        config_fn=config_fn,
        iterations=1,
        messages_per_conversation=0,
        pipeline_index=1,
    )

    assert captured == [[10, 20, 30]]
    assert results[0].document_ids == [10, 20, 30]
    session_payload = fake.posted[0][1]["json"]
    assert "documents" not in session_payload["parameters"]
    attach_url, attach_kwargs = fake.posted[1]
    assert attach_url == "/api/v1/rag/sessions/7/documents"
    assert attach_kwargs["json"] == {"document_ids": [10, 20, 30]}


# ── User simulator / optional openai dependency ─────────────────────────


def test_user_simulator_falls_back_without_openai(monkeypatch) -> None:
    """The fallback question pool works when ``openai`` cannot be imported."""
    monkeypatch.setitem(sys.modules, "openai", None)

    from RAG_benchmark.app.conversation import UserSimulator

    simulator = UserSimulator(api_key="", model="deepseek-chat")
    question = simulator.generate_question(None)

    assert isinstance(question, str)
    assert question.strip()


def test_user_simulator_raises_without_openai_on_api_call(monkeypatch) -> None:
    """A real API call without ``openai`` raises a clear RuntimeError."""
    monkeypatch.setitem(sys.modules, "openai", None)

    from RAG_benchmark.app.conversation import UserSimulator

    simulator = UserSimulator(api_key="sk-not-a-real-key", model="deepseek-chat")

    with pytest.raises(RuntimeError, match="openai"):
        simulator.generate_question(None)
