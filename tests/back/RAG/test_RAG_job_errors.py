"""A failed RAG turn says why it failed, as a plain chat turn does (#969).

The chat keeps a failed turn on screen with its error, so ``RAGJob`` stores a
short, readable detail as the turn's output when the pipeline cannot be built
or cannot answer.
"""

import contextlib
import os
import tempfile
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
from DashAI.back.job.RAG_job import RAGJob
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from tests.back.RAG.test_RAG_job_completes_flow import (
    DOC_TEXT,
    _create_test_document,
    _frontend_session_parameters,
)

CONTEXT_ERROR = "Requested tokens (12000) exceed context window of 10000"


class _EmptySchema(BaseSchema):
    """No parameters."""


class _ContextOverflowLLM(TextToTextGenerationTaskModel):
    """Fails to answer the way llama.cpp does when the prompt does not fit."""

    SCHEMA = _EmptySchema

    def __init__(self, **kwargs):
        self.parameters = {}

    def generate(self, prompt):
        raise ValueError(CONTEXT_ERROR)


@pytest.fixture(scope="module", autouse=True)
def register_models(client: TestClient) -> None:
    registry = client.app.container["component_registry"]
    registry.register_component(_ContextOverflowLLM)


def _run_failing_turn(client: TestClient, edit_parameters) -> list:
    """Run one RAG turn and return the failed turn's outputs.

    ``edit_parameters`` changes a valid session configuration in place, so
    the turn fails.
    """
    run_tag = uuid.uuid4().hex[:8]
    suffix = f"_{run_tag}_errors"
    doc_id = _create_test_document(client, suffix=suffix, text=DOC_TEXT)
    file_path = os.path.join(tempfile.gettempdir(), f"test_doc{suffix}.txt")
    parameters = _frontend_session_parameters(
        doc_id, "BM25Retriever", "DefaultRAGGenerationPrompt"
    )
    parameters["generation_model"] = {
        "component": _ContextOverflowLLM.__name__,
        "params": {},
    }
    edit_parameters(parameters)

    session_factory = client.app.container["session_factory"]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(DOC_TEXT)
        with session_factory() as db:
            session = GenerativeSession(
                task_name="RAGTask",
                model_name="RAGPipeline",
                parameters=parameters,
                name=f"job_errors_{run_tag}",
                description=None,
            )
            db.add(session)
            db.commit()
            process = GenerativeProcess(
                session_id=session.id, status=RunStatus.NOT_STARTED
            )
            db.add(process)
            db.commit()
            db.add(
                ProcessData(
                    process_id=process.id,
                    is_input=True,
                    data="Tell me about DashAI",
                    data_type="str",
                )
            )
            db.commit()
            process_id = process.id

        with pytest.raises(JobError):
            RAGJob(generative_process_id=process_id).run()

        with session_factory() as db:
            process = db.get(GenerativeProcess, process_id)
            assert process.status == RunStatus.ERROR
            assert process.progress is None
            return [(o.data_type, o.data) for o in process.output]
    finally:
        with contextlib.suppress(OSError):
            os.remove(file_path)


def test_a_rag_generation_failure_stores_its_detail(client: TestClient):
    outputs = _run_failing_turn(client, lambda parameters: None)

    assert len(outputs) == 1, outputs
    data_type, detail = outputs[0]
    assert data_type == "str"
    assert "Error during RAG pipeline execution" in detail
    assert CONTEXT_ERROR in detail


def test_a_rag_pipeline_that_cannot_be_built_stores_its_detail(client: TestClient):
    outputs = _run_failing_turn(
        client, lambda parameters: parameters.pop("retriever_model")
    )

    assert len(outputs) == 1, outputs
    data_type, detail = outputs[0]
    assert data_type == "str"
    assert "Error during RAG pipeline setup" in detail
    assert "retriever_model" in detail
