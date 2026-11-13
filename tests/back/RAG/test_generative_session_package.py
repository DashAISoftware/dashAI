"""Round trip of a generative session through a ``.dashai`` file.

Exporting writes the configuration and, when asked, the conversation;
importing creates a new session with the same task, model and parameters,
under a free name, and without documents.
"""

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import (
    DataDocument,
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
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


def test_rag_session_round_trip_reuses_the_same_document(client: TestClient):
    payload = {**_base_session_params(), "name": "Package Round Trip"}
    session_id, document_id = _create_session_with_document(client, payload)
    original = client.get(f"/api/v1/generative-session/{session_id}").json()

    content = _export(client, session_id)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        recipe = json.loads(archive.read("generative_session.json"))
        names = archive.namelist()
    assert manifest["kind"] == "generative_session"
    assert recipe["session"]["parameters"]["documents"] == []
    assert [d["ref"] for d in recipe["documents"]] == [document_id]
    assert any(name.startswith("documents/0/document/") for name in names)

    response = _import(client, content)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["session_name"] == "Package Round Trip (2)"
    assert result["renamed"] is True
    assert result["task_name"] == "RAGTask"
    assert result["document_count"] == 1
    assert result["reused_document_count"] == 1

    imported = client.get(f"/api/v1/generative-session/{result['session_id']}").json()
    assert imported["task_name"] == original["task_name"]
    assert imported["model_name"] == original["model_name"]
    assert imported["parameters"] == original["parameters"]

    linked = client.get(f"/api/v1/rag/sessions/{result['session_id']}/documents")
    assert [d["id"] for d in linked.json()] == [document_id]
    status = client.get(f"/api/v1/rag/sessions/{result['session_id']}/index-status")
    assert status.json()["status"] == "not_indexed"
    assert status.json()["needs_reindex"] is True


def test_rag_document_is_copied_when_not_already_here(client: TestClient):
    payload = {**_base_session_params(), "name": "Package Copy"}
    session_id, document_id = _create_session_with_document(client, payload)
    content = _export(client, session_id)

    # The same file parsed another way, or one this DashAI never saw.
    with client.app.container["session_factory"]() as db:
        db.get(DataDocument, document_id).file_hash = "another file"
        db.commit()

    response = _import(client, content)
    assert response.status_code == 201, response.text
    assert response.json()["reused_document_count"] == 0

    (copy,) = client.get(
        f"/api/v1/rag/sessions/{response.json()['session_id']}/documents"
    ).json()
    assert copy["id"] != document_id
    original = client.get(f"/api/v1/documents/{document_id}").json()
    assert copy["name"] == f"{original['name']} (2)"
    content_response = client.get(f"/api/v1/documents/{copy['id']}/content")
    assert content_response.status_code == 200, content_response.text


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


def _image_session(client: TestClient, name: str) -> int:
    """An image session with one finished exchange: a prompt and its image."""
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
            "name": name,
        },
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    images_path = Path(client.app.container["config"]["IMAGES_PATH"])
    images_path.mkdir(parents=True, exist_ok=True)
    (images_path / "original.png").write_bytes(b"png bytes")
    with client.app.container["session_factory"]() as db:
        process = GenerativeProcess(session_id=session_id, status=RunStatus.FINISHED)
        db.add(process)
        db.flush()
        db.add_all(
            [
                ProcessData(
                    process_id=process.id, is_input=True, data="a cat", data_type="str"
                ),
                ProcessData(
                    process_id=process.id,
                    is_input=False,
                    data="original.png",
                    data_type="Image",
                ),
            ]
        )
        db.add(GenerativeProcess(session_id=session_id, status=RunStatus.ERROR))
        db.commit()
    return session_id


def test_conversation_round_trip(client: TestClient):
    session_id = _image_session(client, "Conversation Round Trip")

    preview = client.get(f"/api/v1/generative-session/{session_id}/export/preview")
    assert preview.json()["message_count"] == 1
    assert preview.json()["unfinished_count"] == 1
    assert preview.json()["media_size_bytes"] == len(b"png bytes")

    response = client.post(
        f"/api/v1/generative-session/{session_id}/export",
        json={"include_conversation": True},
    )
    assert response.status_code == 200, response.text
    imported = _import(client, response.content)
    assert imported.status_code == 201, imported.text
    assert imported.json()["message_count"] == 1

    with client.app.container["session_factory"]() as db:
        (process,) = (
            db.query(GenerativeProcess)
            .filter_by(session_id=imported.json()["session_id"])
            .all()
        )
        assert [(row.data, row.data_type) for row in process.input] == [
            ("a cat", "str")
        ]
        (image,) = process.output
    assert image.data_type == "Image"
    assert image.data != "original.png"
    images_path = Path(client.app.container["config"]["IMAGES_PATH"])
    assert (images_path / image.data).read_bytes() == b"png bytes"


def test_media_outside_the_package_is_refused(client: TestClient):
    session_id = _image_session(client, "Escaping Media")
    content = client.post(
        f"/api/v1/generative-session/{session_id}/export",
        json={"include_conversation": True},
    ).content

    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(content)) as source,
        zipfile.ZipFile(buffer, "w") as target,
    ):
        for name in source.namelist():
            data = source.read(name)
            if name == "generative_session.json":
                recipe = json.loads(data)
                recipe["processes"][0]["output"][0]["media_entry"] = "../secret.png"
                data = json.dumps(recipe)
            target.writestr(name, data)

    response = _import(client, buffer.getvalue())
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_file"


def test_rag_citations_point_at_the_imported_documents(client: TestClient):
    payload = {**_base_session_params(), "name": "Package Citations"}
    session_id, document_id = _create_session_with_document(client, payload)
    ref, gone = f"{document_id}_3", "999999_1"
    with client.app.container["session_factory"]() as db:
        process = GenerativeProcess(session_id=session_id, status=RunStatus.FINISHED)
        db.add(process)
        db.flush()
        rows = [
            (True, "str", "what is DashAI?"),
            (
                False,
                "Dict",
                json.dumps(
                    {
                        ref: {"document_id": document_id, "text": "a"},
                        gone: {"document_id": 999999, "text": "b"},
                    }
                ),
            ),
            (
                False,
                "Trace",
                json.dumps(
                    [
                        {
                            "query": ref,
                            "retriever": {
                                "chunks": [ref, gone],
                                "scores": {ref: 0.9},
                            },
                        }
                    ]
                ),
            ),
            (False, "str", "A toolbox."),
        ]
        db.add_all(
            ProcessData(process_id=process.id, is_input=i, data_type=t, data=d)
            for i, t, d in rows
        )
        db.commit()

    content = client.post(
        f"/api/v1/generative-session/{session_id}/export",
        json={"include_conversation": True},
    ).content
    with client.app.container["session_factory"]() as db:
        db.get(DataDocument, document_id).file_hash = "not the same file"
        db.commit()
    imported = _import(client, content)
    assert imported.status_code == 201, imported.text

    with client.app.container["session_factory"]() as db:
        new_id = db.get(GenerativeSession, imported.json()["session_id"]).parameters[
            "documents"
        ][0]
        (process,) = (
            db.query(GenerativeProcess)
            .filter_by(session_id=imported.json()["session_id"])
            .all()
        )
        output = {
            row.data_type: json.loads(row.data)
            for row in process.output
            if row.data_type in ("Dict", "Trace")
        }
    assert new_id != document_id
    new_ref = f"{new_id}_3"
    assert output["Dict"] == {
        new_ref: {"document_id": new_id, "text": "a"},
        "missing-999999_1": {"document_id": None, "text": "b"},
    }
    assert output["Trace"] == [
        {
            "query": ref,
            "retriever": {
                "chunks": [new_ref, "missing-999999_1"],
                "scores": {new_ref: 0.9},
            },
        }
    ]
