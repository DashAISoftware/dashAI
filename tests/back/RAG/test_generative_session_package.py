"""Round trip of a generative session through a ``.dashai`` file.

Exporting writes only the configuration; importing creates a new session with
the same task, model and parameters, under a free name, and without documents.
"""

import io
import json
import zipfile

from fastapi.testclient import TestClient

from tests.back.RAG.conftest import _create_session_with_document
from tests.back.RAG.test_RAG_session_flow import _base_session_params


def _export(client: TestClient, session_id: int) -> bytes:
    response = client.post(f"/api/v1/generative-session/{session_id}/export")
    assert response.status_code == 200, response.text
    return response.content


def _import(client: TestClient, content: bytes):
    return client.post(
        "/api/v1/generative-session/import",
        files={"file": ("session.dashai", content, "application/zip")},
    )


def test_rag_session_round_trip(client: TestClient):
    payload = {**_base_session_params(), "name": "Package Round Trip"}
    session_id, _ = _create_session_with_document(client, payload)
    original = client.get(f"/api/v1/generative-session/{session_id}").json()

    content = _export(client, session_id)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        recipe = json.loads(archive.read("generative_session.json"))
    assert manifest["kind"] == "generative_session"
    assert recipe["session"]["parameters"]["documents"] == []

    response = _import(client, content)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["session_name"] == "Package Round Trip (2)"
    assert result["renamed"] is True

    imported = client.get(f"/api/v1/generative-session/{result['session_id']}").json()
    assert imported["task_name"] == original["task_name"]
    assert imported["model_name"] == original["model_name"]
    expected = {**original["parameters"], "documents": []}
    assert imported["parameters"] == expected

    history = client.get(
        f"/api/v1/generative-session/{result['session_id']}/parameters-history"
    )
    assert history.status_code == 200


def test_import_refuses_a_model_session_file(client: TestClient):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "manifest.json", json.dumps({"kind": "session", "format_version": 3})
        )
    response = _import(client, buffer.getvalue())
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "wrong_kind"


def test_export_unknown_session_is_404(client: TestClient):
    response = client.post("/api/v1/generative-session/999999/export")
    assert response.status_code == 404


def test_non_rag_session_round_trip(client: TestClient):
    created = client.post(
        "/api/v1/generative-session/",
        json={
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
            "name": "Image Round Trip",
            "description": "kept",
        },
    )
    assert created.status_code == 201, created.text
    original = created.json()

    response = _import(client, _export(client, original["id"]))
    assert response.status_code == 201, response.text
    imported = client.get(
        f"/api/v1/generative-session/{response.json()['session_id']}"
    ).json()
    assert imported["parameters"] == original["parameters"]
    assert imported["description"] == "kept"
