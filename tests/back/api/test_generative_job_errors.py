"""A failed chat turn says why it failed, and never reaches the history (#969).

The chat keeps a failed turn on screen with its error, so every point where
``GenerativeJob`` can fail stores a short, readable detail as the turn's output,
not only ``model.generate``. A failed turn is not part of the history sent to
the model on the next turn.

Lives under ``tests/back/api`` to reuse the ``client`` fixture from this
package's ``conftest.py``.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.job.generative_failure import ERROR_DETAIL_MAX_LENGTH
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

CONTEXT_ERROR = "Requested tokens (900) exceed context window of 512"

#: The prompts the recording model received, one per generate() call.
_PROMPTS: list = []


class _EmptySchema(BaseSchema):
    """No parameters."""


class _RecordingModel(TextToTextGenerationTaskModel):
    """Answers every prompt, and records it."""

    SCHEMA = _EmptySchema

    def __init__(self, **kwargs):
        self.parameters = dict(kwargs)

    def generate(self, prompt):
        _PROMPTS.append(prompt)
        return ["an answer"]


class _ContextOverflowModel(_RecordingModel):
    """Fails to generate the way llama.cpp does when the prompt does not fit."""

    def generate(self, prompt):
        raise ValueError(CONTEXT_ERROR)


class _BrokenInitModel(_RecordingModel):
    """Cannot be built with the session's parameters."""

    def __init__(self, **kwargs):
        raise TypeError("unexpected keyword argument 'n_ctx'")


class _VerboseFailureModel(_RecordingModel):
    """Fails with a message far longer than a chat bubble should show."""

    def generate(self, prompt):
        raise RuntimeError("x" * 5000)


@pytest.fixture(scope="module", autouse=True)
def register_models(client: TestClient) -> None:
    registry = client.app.container["component_registry"]
    for model in (
        _RecordingModel,
        _ContextOverflowModel,
        _BrokenInitModel,
        _VerboseFailureModel,
    ):
        registry.register_component(model)


def _session(client: TestClient, model: type) -> int:
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            task_name="TextToTextGenerationTask",
            model_name=model.__name__,
            parameters={},
            name=f"errors_{uuid.uuid4().hex[:8]}",
            description=None,
        )
        db.add(session)
        db.commit()
        return session.id


def _turn(client: TestClient, session_id: int, text: str, status=None, output=None):
    """Store a turn: its input and, when given, its status and output."""
    with client.app.container["session_factory"]() as db:
        process = GenerativeProcess(
            session_id=session_id, status=status or RunStatus.NOT_STARTED
        )
        db.add(process)
        db.commit()
        db.add(
            ProcessData(
                process_id=process.id, is_input=True, data=text, data_type="str"
            )
        )
        if output is not None:
            db.add(
                ProcessData(
                    process_id=process.id,
                    is_input=False,
                    data=output,
                    data_type="str",
                )
            )
        db.commit()
        return process.id


def _run(process_id: int) -> None:
    GenerativeJob(generative_process_id=process_id).run()


def _failed_output(client: TestClient, process_id: int) -> str:
    with client.app.container["session_factory"]() as db:
        process = db.get(GenerativeProcess, process_id)
        assert process.status == RunStatus.ERROR
        outputs = [data.data for data in process.output]
    assert len(outputs) == 1, outputs
    return outputs[0]


def test_a_generation_failure_stores_its_detail(client: TestClient):
    process_id = _turn(client, _session(client, _ContextOverflowModel), "hi")

    with pytest.raises(JobError):
        _run(process_id)

    assert CONTEXT_ERROR in _failed_output(client, process_id)


def test_a_model_that_cannot_be_built_stores_its_detail(client: TestClient):
    process_id = _turn(client, _session(client, _BrokenInitModel), "hi")

    with pytest.raises(JobError):
        _run(process_id)

    detail = _failed_output(client, process_id)
    assert "Error instantiating model with given parameters." in detail
    assert "unexpected keyword argument 'n_ctx'" in detail


def test_a_long_error_detail_is_cut(client: TestClient):
    process_id = _turn(client, _session(client, _VerboseFailureModel), "hi")

    with pytest.raises(JobError):
        _run(process_id)

    assert len(_failed_output(client, process_id)) <= ERROR_DETAIL_MAX_LENGTH


def test_a_failed_turn_is_left_out_of_the_history(client: TestClient):
    session_id = _session(client, _RecordingModel)
    _turn(client, session_id, "kept question", RunStatus.FINISHED, "kept answer")
    _turn(client, session_id, "failed question", RunStatus.ERROR, "Error details: x")
    process_id = _turn(client, session_id, "new question")
    _PROMPTS.clear()

    _run(process_id)

    prompt = str(_PROMPTS[-1])
    assert "kept question" in prompt
    assert "failed question" not in prompt


def _retry(client: TestClient, process_id: int):
    return client.post(f"/api/v1/generative-process/{process_id}/retry")


def test_retrying_a_failed_turn_runs_it_again_in_place(client: TestClient):
    """The same turn, with its input, is queued again: it keeps its place in
    the conversation and needs no new upload of its files."""
    session_id = _session(client, _RecordingModel)
    process_id = _turn(
        client, session_id, "the question", RunStatus.ERROR, "Error details: x"
    )

    response = _retry(client, process_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == process_id
    assert body["status"] == RunStatus.NOT_STARTED.value
    assert [data["data"] for data in body["input"]] == ["the question"]
    assert body["output"] == []

    _run(process_id)
    with client.app.container["session_factory"]() as db:
        process = db.get(GenerativeProcess, process_id)
        assert process.status == RunStatus.FINISHED
        assert [data.data for data in process.output] == ["an answer"]


def test_only_a_failed_turn_can_be_retried(client: TestClient):
    session_id = _session(client, _RecordingModel)
    process_id = _turn(client, session_id, "q", RunStatus.FINISHED, "an answer")

    response = _retry(client, process_id)

    assert response.status_code == 409, response.text


def test_retrying_a_missing_turn_answers_404(client: TestClient):
    assert _retry(client, 999999).status_code == 404
