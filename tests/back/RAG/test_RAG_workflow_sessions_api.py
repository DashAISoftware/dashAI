"""RAG sessions as text to text sessions run by ``RAGWorkflow``.

The session row names the text to text task and the generation LLM; the
workflow decides how a turn runs and which session steps apply.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    GenerativeSessionParameterHistory,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.job.generative_job import GenerativeJob
from DashAI.back.job.RAG_job import RAGJob
from tests.back.RAG.conftest import (
    BOW_PARAMS,
    RAG_WORKFLOW_PAYLOAD,
    _add_document_to_session,
    assert_rag_identity,
)

GENERATOR = "Llama32_1BInstruct"
OTHER_GENERATOR = "Qwen25_05BInstruct"
SESSIONS = "/api/v1/generative-session/"


def _generation_model(component: str = GENERATOR) -> dict:
    """Return a generation model reference.

    Parameters
    ----------
    component : str
        LLM component name.

    Returns
    -------
    dict
        ``{component, params}`` reference.
    """
    return {
        "component": component,
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    }


def _payload(**overrides) -> dict:
    """Return a RAG session payload with a unique name.

    Parameters
    ----------
    **overrides
        Top level keys replacing the defaults.

    Returns
    -------
    dict
        The POST body.
    """
    payload = {
        **RAG_WORKFLOW_PAYLOAD,
        "name": f"rag_workflow_{uuid.uuid4().hex[:8]}",
        "description": None,
        "parameters": {
            "chunking_model": {
                "component": "CharacterChunkModel",
                "params": {"chunk_size": 400, "chunk_overlap": 40},
            },
            "retriever_model": {
                "component": "BM25Retriever",
                "params": {
                    "vectorizer": {
                        "component": "BagOfWordsConverter",
                        "params": dict(BOW_PARAMS),
                    },
                    "k1": 1.5,
                    "b": 0.75,
                    "delta": 0.0,
                    "similarity_function": "cosine",
                    "top_k": 5,
                },
            },
            "generation_model": _generation_model(),
            "prompt": {
                "component": "DefaultRAGGenerationPrompt",
                "params": {"language": "en"},
            },
        },
    }
    payload.update(overrides)
    return payload


def _create(client: TestClient, **overrides) -> dict:
    """Create a RAG session and return the response body.

    Parameters
    ----------
    client : TestClient
        API client.
    **overrides
        Top level keys replacing the payload defaults.

    Returns
    -------
    dict
        The created session.
    """
    response = client.post(
        SESSIONS, json=_payload(**overrides), headers={"Accept-Language": "en"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _stored(client: TestClient, session_id: int) -> GenerativeSession:
    """Load a session row.

    Parameters
    ----------
    client : TestClient
        API client.
    session_id : int
        Session id.

    Returns
    -------
    GenerativeSession
        The detached row.
    """
    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        db.expunge(session)
        return session


def _create_process(client: TestClient, session_id: int) -> int:
    """Create a turn for a session and return the process id.

    Parameters
    ----------
    client : TestClient
        API client.
    session_id : int
        Session id.

    Returns
    -------
    int
        The process id.
    """
    response = client.post(
        "/api/v1/generative-process/",
        data={"session_id": session_id, "text_0": "What is DashAI?"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_derives_task_and_model_from_the_workflow(client: TestClient):
    """The row names the text to text task and the generation LLM."""
    data = _create(client)

    assert_rag_identity(data, GENERATOR)
    assert data["display_name"] == "Retrieval-Augmented Generation"


def test_create_accepts_the_task_and_model_it_derives(client: TestClient):
    """Sending the same task and model as the workflow derives is fine."""
    data = _create(client, task_name="TextToTextGenerationTask", model_name=GENERATOR)

    assert_rag_identity(data, GENERATOR)


def test_create_rejects_another_task(client: TestClient):
    """A RAG session cannot claim a task other than text to text."""
    response = client.post(SESSIONS, json=_payload(task_name="ControlNetTask"))

    assert response.status_code == 400, response.text
    assert "TextToTextGenerationTask" in response.json()["detail"]


def test_create_rejects_a_model_other_than_the_generator(client: TestClient):
    """The session model is the generator; a different one is refused."""
    response = client.post(SESSIONS, json=_payload(model_name=OTHER_GENERATOR))

    assert response.status_code == 400, response.text
    assert GENERATOR in response.json()["detail"]


def test_create_rejects_a_generator_outside_the_task(client: TestClient):
    """The generator must be a model of the text to text task."""
    payload = _payload()
    payload["parameters"]["generation_model"] = {
        "component": "StableDiffusion2",
        "params": {},
    }

    response = client.post(SESSIONS, json=payload)

    assert response.status_code == 400, response.text
    assert "StableDiffusion2" in response.json()["detail"]


def test_create_rejects_an_unknown_workflow(client: TestClient):
    """Only registered workflows can run a session."""
    response = client.post(SESSIONS, json=_payload(workflow_name="GhostWorkflow"))

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Workflow GhostWorkflow is not registered."


def test_get_returns_the_workflow(client: TestClient):
    """Reading a session shows the workflow that runs it."""
    session_id = _create(client)["id"]

    response = client.get(f"{SESSIONS}{session_id}")

    assert response.status_code == 200
    assert response.json()["workflow_name"] == "RAGWorkflow"


def test_list_filters_by_workflow(client: TestClient):
    """The RAG entry point lists only RAG sessions."""
    session_id = _create(client)["id"]

    rag = client.get(SESSIONS, params={"workflow_name": "RAGWorkflow"}).json()
    inference = client.get(SESSIONS, params={"workflow_name": "InferenceWorkflow"})

    assert session_id in {session["id"] for session in rag}
    assert {session["workflow_name"] for session in rag} == {"RAGWorkflow"}
    assert session_id not in {session["id"] for session in inference.json()}


def test_update_follows_a_new_generator(client: TestClient):
    """Changing the generator changes the session model and its history."""
    session_id = _create(client)["id"]

    response = client.put(
        f"{SESSIONS}{session_id}/parameters",
        json={"generation_model": _generation_model(OTHER_GENERATOR)},
    )

    assert response.status_code == 200, response.text
    assert _stored(client, session_id).model_name == OTHER_GENERATOR
    with client.app.container["session_factory"]() as db:
        latest = (
            db.query(GenerativeSessionParameterHistory)
            .filter(GenerativeSessionParameterHistory.session_id == session_id)
            .order_by(GenerativeSessionParameterHistory.id.desc())
            .first()
        )
        assert latest.model_name == OTHER_GENERATOR


def test_update_rejects_a_generator_outside_the_task(client: TestClient):
    """An update cannot swap in a model of another task."""
    session_id = _create(client)["id"]

    response = client.put(
        f"{SESSIONS}{session_id}/parameters",
        json={"generation_model": {"component": "StableDiffusion2", "params": {}}},
    )

    assert response.status_code == 400, response.text
    stored = _stored(client, session_id)
    assert stored.model_name == GENERATOR
    assert stored.parameters["generation_model"]["component"] == GENERATOR


def test_patch_refuses_a_model_switch(client: TestClient):
    """The generator is changed through the parameters, not the model switch."""
    data = _create(client)

    response = client.patch(
        f"{SESSIONS}{data['id']}",
        params={"name": f"{data['name']}_renamed", "model_name": OTHER_GENERATOR},
    )

    assert response.status_code == 400, response.text
    stored = _stored(client, data["id"])
    assert stored.name == data["name"]
    assert stored.model_name == GENERATOR


def test_patch_still_renames(client: TestClient):
    """Renaming a RAG session keeps working."""
    data = _create(client)
    new_name = f"{data['name']}_renamed"

    response = client.patch(f"{SESSIONS}{data['id']}", params={"name": new_name})

    assert response.status_code == 200, response.text
    assert _stored(client, data["id"]).name == new_name


def test_history_shows_a_generator_change_as_a_parameter_change(client: TestClient):
    """A generator change lists the changed parameters, not only the model."""
    session_id = _create(client)["id"]
    client.put(
        f"{SESSIONS}{session_id}/parameters",
        json={"generation_model": _generation_model(OTHER_GENERATOR)},
    )

    events = client.get(f"{SESSIONS}parameters-history/{session_id}").json()

    changed = {change["parameter"] for change in events[-1]["changes"]}
    assert "generation_model" in changed
    assert "model" not in changed


def test_a_turn_without_documents_is_refused(client: TestClient):
    """The RAG session service refuses a turn over no documents."""
    session_id = _create(client)["id"]

    response = client.post(
        "/api/v1/generative-process/",
        data={"session_id": session_id, "text_0": "What is DashAI?"},
    )

    assert response.status_code == 400, response.text
    assert "Add at least one document" in response.json()["detail"]


def test_generative_job_hands_a_rag_turn_to_the_rag_job(
    client: TestClient, monkeypatch
):
    """The job named by the workflow runs the turn."""
    session_id = _create(client)["id"]
    _add_document_to_session(client, session_id, suffix=uuid.uuid4().hex[:8])
    process_id = _create_process(client, session_id)
    ran = []
    monkeypatch.setattr(RAGJob, "run", lambda self: ran.append(self.kwargs))

    GenerativeJob(generative_process_id=process_id).run()

    assert ran == [{"generative_process_id": process_id}]


def test_generative_job_refuses_an_unknown_workflow(client: TestClient):
    """A session whose workflow is gone fails the turn instead of guessing."""
    session_id = _create(client)["id"]
    _add_document_to_session(client, session_id, suffix=uuid.uuid4().hex[:8])
    process_id = _create_process(client, session_id)
    with client.app.container["session_factory"]() as db:
        db.get(GenerativeSession, session_id).workflow_name = "GhostWorkflow"
        db.commit()

    with pytest.raises(JobError, match="GhostWorkflow"):
        GenerativeJob(generative_process_id=process_id).run()

    with client.app.container["session_factory"]() as db:
        assert db.get(GenerativeProcess, process_id).status == RunStatus.ERROR
