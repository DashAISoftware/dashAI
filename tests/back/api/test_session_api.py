import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module", name="response_1")
def create_session_1(client: TestClient):
    """Create testing session 1 using job system."""
    params = {
        "model_name": "StableDiffusion2",
        "task_name": "TextToImageGenerationTask",
        "parameters": {
            "num_inference_steps": 1,
            "model_name": "sd2-community/stable-diffusion-2",
            "guidance_scale": 6.0,
            "device": "CPU",
            "negative_prompt": "",
            "seed": 42,
            "width": 256,
            "height": 256,
            "num_images_per_prompt": 1,
        },
        "name": "session_1",
        "description": None,
    }

    response = client.post(
        "/api/v1/generative-session/",
        json=params,
    )

    return response


@pytest.fixture(scope="module", name="response_2")
def create_session_2(client: TestClient):
    """Create testing session 2 using job system."""
    params = {
        "model_name": "SomeModel",
        "task_name": "ImageGenerationTask",
        "parameters": {
            "num_inference_steps": 1,
        },
        "name": "session_2",
        "description": None,
    }

    response = client.post(
        "/api/v1/generative-session/",
        json=params,
    )

    return response


@pytest.fixture(scope="module", name="response_3")
def create_session_3(client: TestClient):
    """Create testing session 3 using a non-download-required model."""
    params = {
        "model_name": "StableDiffusion2",
        "task_name": "TextToImageGenerationTask",
        "parameters": {
            "num_inference_steps": 1,
            "model_name": "sd2-community/stable-diffusion-2",
            "guidance_scale": 6.0,
            "device": "CPU",
            "negative_prompt": "",
            "seed": 42,
            "width": 256,
            "height": 256,
            "num_images_per_prompt": 1,
        },
        "name": "session_3",
        "description": None,
    }

    response = client.post(
        "/api/v1/generative-session/",
        json=params,
    )

    return response


@pytest.fixture(scope="module", name="response_4")
def create_session_4(client: TestClient):
    """Create testing session 4 with an invalid task (valid model)."""
    params = {
        "model_name": "StableDiffusion2",
        "task_name": "SomeTask",
        "parameters": {
            "num_inference_steps": 1,
            "model_name": "sd2-community/stable-diffusion-2",
            "guidance_scale": 6.0,
            "device": "CPU",
            "negative_prompt": "",
            "seed": 42,
            "width": 256,
            "height": 256,
            "num_images_per_prompt": 1,
        },
        "name": "session_4",
        "description": None,
    }

    response = client.post(
        "/api/v1/generative-session/",
        json=params,
    )

    return response


def test_create_session(response_1):
    """Test creating a session."""
    assert response_1.status_code == 201, "Session creation failed"
    data = response_1.json()
    assert data["id"] is not None, "Session ID is missing"
    assert data["name"] == "session_1", "Session name does not match"
    assert data["model_name"] == "StableDiffusion2", "Model name does not match"
    assert data["task_name"] == "TextToImageGenerationTask", "Task name does not match"


def test_create_session_with_invalid_model(response_2):
    """Test creating a session with an invalid model."""
    assert response_2.status_code == 400
    assert response_2.json()["detail"] == "Model SomeModel is not registered."


def test_get_session_by_id(client: TestClient, response_1):
    """Test retrieving a session by ID."""
    session_id = response_1.json()["id"]
    response = client.get(f"/api/v1/generative-session/{session_id}")

    assert response.status_code == 200, "Failed to retrieve session by ID"
    data = response.json()
    assert data["id"] == session_id, "Retrieved session ID does not match"
    assert data["name"] == "session_1", "Session name does not match"
    assert data["model_name"] == "StableDiffusion2", "Model name does not match"
    assert data["task_name"] == "TextToImageGenerationTask", "Task name does not match"


def test_get_non_existent_session(client: TestClient):
    """Test retrieving a non-existent session."""
    non_existent_id = 9999
    response = client.get(f"/api/v1/generative-session/{non_existent_id}")

    assert response.status_code == 404, "Expected 404 for non-existent session"
    assert response.json()["detail"] == "Generative session 9999 does not exist in DB."


def test_get_all_sessions(
    client: TestClient,
    response_1,
    response_3,
):
    """Test retrieving all sessions."""
    response = client.get("/api/v1/generative-session/")

    assert response.status_code == 200, "Failed to retrieve all sessions"
    data = response.json()

    assert len(data) == 2, "Expected 2 sessions"

    session_ids = {session["id"] for session in data}
    assert response_1.json()["id"] in session_ids, "Session 1 not found in all sessions"
    assert response_3.json()["id"] in session_ids, "Session 3 not found in all sessions"


def test_create_session_with_invalid_task(response_4):
    """Test creating a session with an invalid task."""
    assert response_4.status_code == 400
    assert response_4.json()["detail"] == "Task SomeTask is not registered."
