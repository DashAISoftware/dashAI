"""A chat that outgrows the context window folds its oldest turns into a
summary stored on the session, and sends it first (#977).

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
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.job.history_summary import SUMMARY_ACK, SUMMARY_PREFIX
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

MARKER = "Summarize the conversation below."
CONTEXT_ERROR = "Requested tokens (900) exceed context window of 512"

#: The prompts the models received, one per generate() call.
_PROMPTS: list = []


class _EmptySchema(BaseSchema):
    """No parameters."""


class _WordCountingModel(TextToTextGenerationTaskModel):
    """Counts one token per word; window 200, reply reserve 20 (budget 180)."""

    SCHEMA = _EmptySchema

    def __init__(self, **kwargs):
        self.max_tokens = 20

    def context_limits(self):
        return (200, self.max_tokens)

    def count_tokens(self, messages):
        return sum(len(m["content"].split()) for m in messages)

    def generate(self, prompt):
        _PROMPTS.append(prompt)
        if prompt[0]["content"].startswith(MARKER):
            return [f"S{len(_PROMPTS)}"]
        return ["an answer"]


class _LargeReplyModel(_WordCountingModel):
    """Asks for a reply as long as the whole window, which llama.cpp clamps."""

    def __init__(self, **kwargs):
        self.max_tokens = 200


class _NoCountModel(_WordCountingModel):
    def count_tokens(self, messages):
        return None


class _FailingSummaryModel(_WordCountingModel):
    def generate(self, prompt):
        if prompt[0]["content"].startswith(MARKER):
            raise RuntimeError("summary failed")
        return ["an answer"]


class _EmptySummaryModel(_WordCountingModel):
    def generate(self, prompt):
        _PROMPTS.append(prompt)
        if prompt[0]["content"].startswith(MARKER):
            return ["  "]
        return ["an answer"]


class _ContextOverflowModel(_WordCountingModel):
    """Fails to generate the way llama.cpp does when the prompt does not fit."""

    def context_limits(self):
        return None

    def generate(self, prompt):
        raise ValueError(CONTEXT_ERROR)


@pytest.fixture(scope="module", autouse=True)
def register_models(client: TestClient) -> None:
    registry = client.app.container["component_registry"]
    for model in (
        _WordCountingModel,
        _LargeReplyModel,
        _NoCountModel,
        _FailingSummaryModel,
        _EmptySummaryModel,
        _ContextOverflowModel,
    ):
        registry.register_component(model)


def _words(label: str, n: int = 30) -> str:
    return " ".join(f"{label}w{i}" for i in range(n))


def _session(client: TestClient, model: type, summary=None, until=None) -> int:
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            task_name="TextToTextGenerationTask",
            model_name=model.__name__,
            parameters={},
            name=f"summary_{uuid.uuid4().hex[:8]}",
            description=None,
            history_summary=summary,
            history_summary_until=until,
        )
        db.add(session)
        db.commit()
        return session.id


def _set_summary(client: TestClient, session_id: int, summary, until) -> None:
    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        session.history_summary = summary
        session.history_summary_until = until
        db.commit()


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


def _finished_turns(client: TestClient, session_id: int, start: int, n: int):
    """Store ``n`` finished turns of 60 words each, labelled from ``start``."""
    return [
        _turn(
            client,
            session_id,
            _words(f"q{i}"),
            RunStatus.FINISHED,
            _words(f"a{i}"),
        )
        for i in range(start, start + n)
    ]


def _run(process_id: int) -> None:
    GenerativeJob(generative_process_id=process_id).run()


def _summary(client: TestClient, session_id: int):
    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        return session.history_summary, session.history_summary_until


def _status(client: TestClient, process_id: int):
    with client.app.container["session_factory"]() as db:
        return db.get(GenerativeProcess, process_id).status


def _failed_output(client: TestClient, process_id: int) -> str:
    with client.app.container["session_factory"]() as db:
        process = db.get(GenerativeProcess, process_id)
        assert process.status == RunStatus.ERROR
        outputs = [data.data for data in process.output]
    assert len(outputs) == 1, outputs
    return outputs[0]


def _summary_prompts(prompts):
    return [p for p in prompts if p[0]["content"].startswith(MARKER)]


def _word_count(prompt) -> int:
    return sum(len(m["content"].split()) for m in prompt)


def test_max_tokens_as_large_as_the_window_still_answers(client: TestClient):
    session_id = _session(client, _LargeReplyModel)
    _turn(client, session_id, "hello there", RunStatus.FINISHED, "hi, how can I help")
    process_id = _turn(client, session_id, "hi")
    _PROMPTS.clear()

    _run(process_id)

    assert _status(client, process_id) == RunStatus.FINISHED
    assert _summary_prompts(_PROMPTS) == []
    assert _summary(client, session_id) == (None, None)


def test_a_model_that_cannot_count_gets_the_full_history(client: TestClient):
    session_id = _session(client, _NoCountModel)
    turns = _finished_turns(client, session_id, 1, 6)
    _set_summary(client, session_id, "old", turns[1])
    process_id = _turn(client, session_id, "new question")
    _PROMPTS.clear()

    _run(process_id)

    expected = [
        {"role": "user", "content": SUMMARY_PREFIX + "old"},
        {"role": "assistant", "content": SUMMARY_ACK},
    ]
    for i in range(3, 7):
        expected.append({"role": "user", "content": _words(f"q{i}")})
        expected.append({"role": "assistant", "content": _words(f"a{i}")})
    expected.append({"role": "user", "content": "new question"})
    assert _PROMPTS[-1] == expected
    assert _summary_prompts(_PROMPTS) == []
    assert _summary(client, session_id) == ("old", turns[1])


def _overflowed_session(client: TestClient):
    session_id = _session(client, _WordCountingModel)
    turns = _finished_turns(client, session_id, 1, 6)
    process_id = _turn(client, session_id, "new question")
    _run(process_id)
    return session_id, turns, process_id


def test_overflow_stores_a_summary_and_sends_it_first(client: TestClient):
    _PROMPTS.clear()
    session_id, turns, process_id = _overflowed_session(client)

    assert _status(client, process_id) == RunStatus.FINISHED
    summary, until = _summary(client, session_id)
    assert summary is not None
    assert until in turns
    prompt = _PROMPTS[-1]
    assert prompt[0] == {"role": "user", "content": SUMMARY_PREFIX + summary}
    assert prompt[1] == {"role": "assistant", "content": SUMMARY_ACK}
    assert _word_count(prompt) <= 180


def test_a_second_overflow_folds_the_previous_summary(client: TestClient):
    _PROMPTS.clear()
    session_id, _, _ = _overflowed_session(client)
    previous, previous_until = _summary(client, session_id)
    _finished_turns(client, session_id, 10, 4)
    process_id = _turn(client, session_id, "another question")
    start = len(_PROMPTS)

    _run(process_id)

    assert _status(client, process_id) == RunStatus.FINISHED
    folded = _summary_prompts(_PROMPTS[start:])
    assert any(previous in p[0]["content"].split() for p in folded)
    _, until = _summary(client, session_id)
    assert until > previous_until


def test_a_message_that_cannot_fit_fails_clearly(client: TestClient):
    session_id = _session(client, _WordCountingModel)
    process_id = _turn(client, session_id, _words("long", 200))

    with pytest.raises(JobError):
        _run(process_id)

    assert _failed_output(client, process_id) == (
        "Conversation too long for the context window (220 of 200 tokens). "
        "Increase context_window or start a new session."
    )


def test_a_long_old_turn_is_cut_before_summarizing(client: TestClient):
    session_id = _session(client, _WordCountingModel)
    _turn(client, session_id, _words("long", 400), RunStatus.FINISHED, "an answer")
    process_id = _turn(client, session_id, "short question")
    _PROMPTS.clear()

    _run(process_id)

    assert _status(client, process_id) == RunStatus.FINISHED
    folded = _summary_prompts(_PROMPTS)
    assert folded
    assert all(_word_count(p) <= 200 - 50 for p in folded)
    assert _summary(client, session_id)[0] is not None


def test_a_failed_summary_keeps_the_previous_one(client: TestClient):
    session_id = _session(client, _FailingSummaryModel)
    turns = _finished_turns(client, session_id, 1, 5)
    _set_summary(client, session_id, "old", turns[0])
    process_id = _turn(client, session_id, "new question")

    with pytest.raises(JobError):
        _run(process_id)

    assert _failed_output(client, process_id).startswith(
        "Error summarizing the conversation history."
    )
    assert _summary(client, session_id) == ("old", turns[0])


def test_an_empty_summary_fails_the_turn(client: TestClient):
    session_id = _session(client, _EmptySummaryModel)
    turns = _finished_turns(client, session_id, 1, 5)
    _set_summary(client, session_id, "old", turns[0])
    process_id = _turn(client, session_id, "new question")

    with pytest.raises(JobError):
        _run(process_id)

    assert _failed_output(client, process_id).startswith(
        "Error summarizing the conversation history."
    )
    assert _summary(client, session_id) == ("old", turns[0])


def test_a_message_that_cannot_fit_fails_before_summarizing(client: TestClient):
    session_id = _session(client, _WordCountingModel)
    _finished_turns(client, session_id, 1, 3)
    process_id = _turn(client, session_id, _words("long", 200))
    _PROMPTS.clear()

    with pytest.raises(JobError):
        _run(process_id)

    assert _failed_output(client, process_id) == (
        "Conversation too long for the context window (220 of 200 tokens). "
        "Increase context_window or start a new session."
    )
    assert _summary_prompts(_PROMPTS) == []


def test_llama_context_error_is_reported_clearly(client: TestClient):
    process_id = _turn(client, _session(client, _ContextOverflowModel), "hi")

    with pytest.raises(JobError):
        _run(process_id)

    detail = _failed_output(client, process_id)
    assert detail.startswith("Conversation too long for the context window.")
    assert CONTEXT_ERROR in detail
