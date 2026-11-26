"""A chat turn stores the usage and finish reason of the model's reply (#976).

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
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.models.generation_result import GenerationResult, TextPart, Usage
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)


class _MetadataEmptySchema(BaseSchema):
    """No parameters."""


class _LegacyTextModel(TextToTextGenerationTaskModel):
    """Only implements ``generate``, as models written before #976 do."""

    SCHEMA = _MetadataEmptySchema

    def __init__(self, **kwargs):
        self.parameters = dict(kwargs)

    def generate(self, prompt):
        return ["legacy"]


class _UsageModel(_LegacyTextModel):
    """Reports usage and a finish reason with its reply."""

    def generate(self, prompt):
        return self.generate_result(prompt).to_outputs()

    def generate_result(self, prompt):
        return GenerationResult(
            parts=(TextPart("hi"),),
            usage=Usage(prompt_tokens=5, completion_tokens=2),
            finish_reason="stop",
        )


@pytest.fixture(scope="module", autouse=True)
def register_models(client: TestClient) -> None:
    registry = client.app.container["component_registry"]
    for model in (_LegacyTextModel, _UsageModel):
        registry.register_component(model)


def _session(client: TestClient, model: type) -> int:
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            task_name="TextToTextGenerationTask",
            model_name=model.__name__,
            parameters={},
            name=f"metadata_{uuid.uuid4().hex[:8]}",
            description=None,
        )
        db.add(session)
        db.commit()
        return session.id


def _turn(client: TestClient, session_id: int, text: str) -> int:
    with client.app.container["session_factory"]() as db:
        process = GenerativeProcess(session_id=session_id, status=RunStatus.NOT_STARTED)
        db.add(process)
        db.commit()
        db.add(
            ProcessData(
                process_id=process.id, is_input=True, data=text, data_type="str"
            )
        )
        db.commit()
        return process.id


def _run(process_id: int) -> None:
    GenerativeJob(generative_process_id=process_id).run()


def test_turn_stores_generation_metadata(client: TestClient):
    pid = _turn(client, _session(client, _UsageModel), "hello")
    _run(pid)

    body = client.get(f"/api/v1/generative-process/{pid}").json()

    assert body["generation_metadata"] == {
        "version": 1,
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        "finish_reason": "stop",
    }
    assert [o["data"] for o in body["output"]] == ["hi"]


def test_legacy_model_stores_no_metadata(client: TestClient):
    pid = _turn(client, _session(client, _LegacyTextModel), "hello")
    _run(pid)

    body = client.get(f"/api/v1/generative-process/{pid}").json()

    assert body["status"] == RunStatus.FINISHED.value
    assert body["generation_metadata"] is None
    assert [o["data"] for o in body["output"]] == ["legacy"]
