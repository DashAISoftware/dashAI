"""Legacy and enriched text models share chat storage and history behavior."""

import contextlib
import uuid

import pytest
from kink import di

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.core.generation import GenerationResult, ReasoningPart, TextPart
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from DashAI.back.tasks.text_to_text_generation_task import TextToTextGenerationTask


@pytest.mark.parametrize("enriched", [False, True])
def test_models_keep_session_parameters_and_plain_text_history(client, enriched):
    prompts = []
    parameters = {"model": "existing-model", "temperature": 0.2}

    class LegacyModel(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            assert kwargs == parameters

        def generate(self, prompt):
            prompts.append(prompt)
            return ["Answer"]

    class TypedModel(LegacyModel):
        def generate_result(self, request):
            prompts.append(request.to_messages())
            return GenerationResult(
                parts=[ReasoningPart(text="Plan"), TextPart(text="Answer")]
            )

        def generate(self, prompt):
            pytest.fail("The enriched model must not call the legacy generation path.")

    registry = di["component_registry"]
    di["component_registry"] = {
        "TextToTextGenerationTask": {"class": TextToTextGenerationTask},
        "InterfaceTestModel": {"class": TypedModel if enriched else LegacyModel},
    }
    session_factory = di["session_factory"]
    try:
        with session_factory() as db:
            session = GenerativeSession(
                name=f"interface-{uuid.uuid4().hex}",
                task_name="TextToTextGenerationTask",
                model_name="InterfaceTestModel",
                parameters=parameters,
            )
            db.add(session)
            db.flush()
            session_id = session.id
            db.commit()

        for question in ("First question", "Follow-up"):
            with session_factory() as db:
                process = GenerativeProcess(session_id=session_id)
                db.add(process)
                db.flush()
                process_id = process.id
                db.add(
                    ProcessData(process_id=process_id, data=question, data_type="str")
                )
                db.commit()

            GenerativeJob(generative_process_id=process_id).run()

            with session_factory() as db:
                process = db.get(GenerativeProcess, process_id)
                assert process.status == RunStatus.FINISHED
                assert len(process.output) == 1
                assert process.output[0].data == "Answer"
                assert process.output[0].data_type == "str"
                assert db.get(GenerativeSession, session_id).parameters == parameters

        assert prompts == [
            [{"role": "user", "content": "First question"}],
            [
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "Answer"},
                {"role": "user", "content": "Follow-up"},
            ],
        ]
    finally:
        di["component_registry"] = registry


def _run_chat_job(client, model_class):
    registry = di["component_registry"]
    di["component_registry"] = {
        "TextToTextGenerationTask": {"class": TextToTextGenerationTask},
        "InterfaceTestModel": {"class": model_class},
    }
    session_factory = di["session_factory"]
    try:
        with session_factory() as db:
            session = GenerativeSession(
                name=f"interface-{uuid.uuid4().hex}",
                task_name="TextToTextGenerationTask",
                model_name="InterfaceTestModel",
                parameters={},
            )
            db.add(session)
            db.flush()
            process = GenerativeProcess(session_id=session.id)
            db.add(process)
            db.flush()
            process_id = process.id
            db.add(ProcessData(process_id=process_id, data="Hi", data_type="str"))
            db.commit()

        with contextlib.suppress(Exception):  # failures surface as JobError
            GenerativeJob(generative_process_id=process_id).run()

        with session_factory() as db:
            process = db.get(GenerativeProcess, process_id)
            return process.status, [o.data for o in process.output]
    finally:
        di["component_registry"] = registry


def test_enriched_failure_is_reported_once_without_legacy_fallback(client):
    calls = []

    class FailingModel(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            pass

        def generate(self, prompt):
            calls.append("generate")
            return ["fallback"]

        def generate_result(self, request):
            calls.append("generate_result")
            raise RuntimeError("provider down")

    status, outputs = _run_chat_job(client, FailingModel)

    assert status == RunStatus.ERROR
    assert calls == ["generate_result"]
    assert "provider down" in outputs[0]


def test_reasoning_only_reply_is_an_error_not_an_empty_answer(client):
    class ReasoningOnlyModel(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            pass

        def generate(self, prompt):
            raise NotImplementedError

        def generate_result(self, request):
            return GenerationResult(parts=[ReasoningPart(text="Plan")])

    status, outputs = _run_chat_job(client, ReasoningOnlyModel)

    assert status == RunStatus.ERROR
    assert outputs == []


def test_legacy_tuple_output_is_stored_as_the_first_reply(client):
    class TupleModel(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            pass

        def generate(self, prompt):
            return ("Answer", "Ignored")

    status, outputs = _run_chat_job(client, TupleModel)

    assert status == RunStatus.FINISHED
    assert outputs == ["Answer"]


def test_process_output_rejects_reasoning_only_reply_with_actionable_message():
    task = TextToTextGenerationTask()
    result = GenerationResult(parts=[ReasoningPart(text="Plan")])

    with pytest.raises(ValueError, match="reasoning but no answer text"):
        task.process_output(result)

    answer = GenerationResult(parts=[ReasoningPart(text="Plan"), TextPart(text="")])
    assert task.process_output(answer) == [("", "str")]
