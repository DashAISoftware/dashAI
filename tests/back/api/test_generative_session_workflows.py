"""Inference sessions and the workflow listing.

Every generative session runs a workflow. A session created the old way, with
a task and a model and no workflow, is an ``InferenceWorkflow`` session.
"""

import pytest
from fastapi.testclient import TestClient

from tests.back.RAG.conftest import _mark_download_required_components_present

SESSIONS = "/api/v1/generative-session/"
SD2_PARAMETERS = {
    "num_inference_steps": 1,
    "model_name": "sd2-community/stable-diffusion-2",
    "guidance_scale": 6.0,
    "device": "CPU",
    "negative_prompt": "",
    "seed": 42,
    "width": 256,
    "height": 256,
    "num_images_per_prompt": 1,
}


@pytest.fixture(scope="module", autouse=True)
def mark_downloads_present(client: TestClient) -> None:
    """Treat every download required component as downloaded."""
    _mark_download_required_components_present(client.app)


def _image_payload(name: str, **overrides) -> dict:
    """Return an inference session payload for Stable Diffusion 2.

    Parameters
    ----------
    name : str
        Session name.
    **overrides
        Top level keys replacing the defaults.

    Returns
    -------
    dict
        The POST body.
    """
    payload = {
        "model_name": "StableDiffusion2",
        "task_name": "TextToImageGenerationTask",
        "parameters": dict(SD2_PARAMETERS),
        "name": name,
        "description": None,
    }
    payload.update(overrides)
    return payload


def test_a_session_without_a_workflow_runs_inference(client: TestClient):
    """The old payload creates an inference session."""
    response = client.post(SESSIONS, json=_image_payload("inference_default"))

    assert response.status_code == 201, response.text
    assert response.json()["workflow_name"] == "InferenceWorkflow"


def test_an_explicit_inference_session_is_the_same(client: TestClient):
    """Naming the inference workflow changes nothing."""
    response = client.post(
        SESSIONS,
        json=_image_payload("inference_explicit", workflow_name="InferenceWorkflow"),
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["workflow_name"] == "InferenceWorkflow"
    assert data["task_name"] == "TextToImageGenerationTask"
    assert data["model_name"] == "StableDiffusion2"


def test_an_inference_session_needs_a_task(client: TestClient):
    """A task agnostic workflow cannot guess the task."""
    payload = _image_payload("inference_no_task", workflow_name="InferenceWorkflow")
    del payload["task_name"]

    response = client.post(SESSIONS, json=payload)

    assert response.status_code == 400, response.text


def test_without_a_workflow_task_and_model_are_required(client: TestClient):
    """The old payload shape still demands a task and a model."""
    payload = _image_payload("inference_no_model")
    del payload["model_name"]

    response = client.post(SESSIONS, json=payload)

    assert response.status_code == 422, response.text


def test_an_inference_model_must_fit_the_task(client: TestClient):
    """A model of another task is refused."""
    response = client.post(
        SESSIONS,
        json=_image_payload(
            "inference_wrong_task", task_name="TextToTextGenerationTask"
        ),
    )

    assert response.status_code == 400, response.text
    assert "StableDiffusion2" in response.json()["detail"]


def test_the_list_filters_inference_sessions(client: TestClient):
    """Filtering by the inference workflow keeps inference sessions."""
    created = client.post(SESSIONS, json=_image_payload("inference_listed")).json()

    listed = client.get(SESSIONS, params={"workflow_name": "InferenceWorkflow"})

    assert created["id"] in {session["id"] for session in listed.json()}
    assert {session["workflow_name"] for session in listed.json()} == {
        "InferenceWorkflow"
    }


def test_generative_tasks_no_longer_include_rag(client: TestClient):
    """RAG is a workflow, so the task list never shows it."""
    response = client.get(
        "/api/v1/component/", params={"select_types": "GenerativeTask"}
    )

    assert response.status_code == 200
    tasks = response.json()
    assert "RAGTask" not in {task["name"] for task in tasks}
    assert all("entry_point" not in task["metadata"] for task in tasks)


def _names(client: TestClient, **params) -> set:
    """List component names through the components API.

    Parameters
    ----------
    client : TestClient
        API client.
    **params
        Query parameters.

    Returns
    -------
    set
        Names of the returned components.
    """
    response = client.get("/api/v1/component/", params=params)
    assert response.status_code == 200, response.text
    return {component["name"] for component in response.json()}


def test_both_workflows_are_listed(client: TestClient):
    """The landing lists the workflows the backend registers."""
    assert _names(client, select_types="GenerativeWorkflow") == {
        "InferenceWorkflow",
        "RAGWorkflow",
    }


def test_each_workflow_relates_the_tasks_it_runs(client: TestClient):
    """The task relation comes from the workflows' compatible components."""
    assert _names(
        client, related_component="RAGWorkflow", select_types="GenerativeTask"
    ) == {"TextToTextGenerationTask"}
    assert _names(
        client, related_component="InferenceWorkflow", select_types="GenerativeTask"
    ) == {
        "TextToTextGenerationTask",
        "TextToImageGenerationTask",
        "ControlNetTask",
    }


def test_the_rag_workflow_relates_its_components(client: TestClient):
    """Retrievers and chunkers are related to the RAG workflow."""
    related = _names(client, related_component="RAGWorkflow")

    assert {"BM25Retriever", "CharacterChunkModel"} <= related


def test_task_models_are_scoped_by_type(client: TestClient):
    """Asking a task for its generative models leaves the workflows out."""
    models = _names(
        client,
        related_component="TextToTextGenerationTask",
        select_types="GenerativeModel",
    )

    assert models
    assert not models & {"InferenceWorkflow", "RAGWorkflow"}


def test_an_inference_session_needs_a_task_its_workflow_runs(client: TestClient):
    """A registered task outside the workflow's tasks is refused."""
    response = client.post(
        SESSIONS,
        json=_image_payload("inference_other_task", task_name="TextClassificationTask"),
    )

    assert response.status_code == 400, response.text
    assert "does not run task TextClassificationTask" in response.json()["detail"]
