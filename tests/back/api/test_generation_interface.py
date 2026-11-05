"""Legacy and enriched text models share chat storage and history behavior."""

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
