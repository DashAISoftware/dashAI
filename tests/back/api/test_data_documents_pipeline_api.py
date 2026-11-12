"""Tests for the converter pipeline of the document create endpoints."""

import json
import uuid

from sqlalchemy import select

from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dependencies.database.models import DataDocument

TEXT_LOADER = "PlainTextDocumentDataLoader"
SPLIT_SENTENCES = [{"converter": "TextSplitter", "params": {"split_by": "Sentences"}}]


def _name(prefix="doc"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _file(name=None, file_name="notes.txt"):
    return {
        "name": name or _name(),
        "file_name": file_name,
        "dataloader": TEXT_LOADER,
        "dataloader_params": {},
    }


def _create(client, **overrides):
    payload = _file()
    payload.update(overrides)
    return client.post("/api/v1/documents/", json=payload)


def _batch(client, files, **overrides):
    payload = {"files": files}
    payload.update(overrides)
    return client.post("/api/v1/documents/batch", json=payload)


def _enqueue(client, document_id, file_name, content):
    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "DocumentJob",
            "kwargs": json.dumps({"document_id": document_id}),
        },
        files={"file": (file_name, content, "application/octet-stream")},
        headers={"filename": file_name},
    )
    assert response.status_code == 201, response.text


def _stored_names(client, names):
    with client.app.container["session_factory"]() as db:
        return list(
            db.execute(
                select(DataDocument.name).where(DataDocument.name.in_(names))
            ).scalars()
        )


def test_create_stores_the_pipeline_and_the_job_applies_it(client):
    name = _name()
    created = _create(client, name=name, converter_pipeline=SPLIT_SENTENCES)

    assert created.status_code == 201, created.text
    assert created.json()["converter_pipeline"] == SPLIT_SENTENCES

    _enqueue(client, created.json()["id"], "notes.txt", b"One. Two.")
    fetched = client.get(f"/api/v1/documents/{created.json()['id']}").json()

    assert fetched["status"] == DocumentStatus.FINISHED.value
    assert fetched["content_counts"] == {"Text": 2}


def test_batch_stores_the_pipeline_and_applies_it_to_every_document(client):
    files = [_file("cap1.txt"), _file("cap2.txt")]
    created = _batch(client, files, converter_pipeline=SPLIT_SENTENCES)

    assert created.status_code == 201, created.text
    body = created.json()
    assert [row["converter_pipeline"] for row in body["documents"]] == [
        SPLIT_SENTENCES,
        SPLIT_SENTENCES,
    ]

    for row, file_name in zip(body["documents"], ["cap1.txt", "cap2.txt"], strict=True):
        _enqueue(client, row["id"], file_name, b"One. Two.")

    for row in body["documents"]:
        fetched = client.get(f"/api/v1/documents/{row['id']}").json()
        assert fetched["status"] == DocumentStatus.FINISHED.value
        assert fetched["content_counts"] == {"Text": 2}


def test_create_rejects_an_unknown_converter_without_a_row(client):
    name = _name()
    response = _create(
        client,
        name=name,
        converter_pipeline=[{"converter": "NopeConverter", "params": {}}],
    )

    assert response.status_code == 422, response.text
    assert _stored_names(client, [name]) == []


def test_batch_rejects_an_unknown_converter_without_rows(client):
    files = [_file(), _file()]
    response = _batch(
        client,
        files,
        converter_pipeline=[{"converter": "NopeConverter", "params": {}}],
    )

    assert response.status_code == 422, response.text
    assert _stored_names(client, [item["name"] for item in files]) == []


def test_create_rejects_invalid_pipeline_params_without_a_row(client):
    name = _name()
    response = _create(
        client,
        name=name,
        converter_pipeline=[
            {"converter": "TextSplitter", "params": {"split_by": "Nope"}}
        ],
    )

    assert response.status_code == 422, response.text
    assert _stored_names(client, [name]) == []


def test_create_rejects_a_converter_that_must_be_downloaded(client, monkeypatch):
    from DashAI.back.converters.document.ocr import OCRConverter

    monkeypatch.setattr(OCRConverter, "is_downloaded", classmethod(lambda cls: False))
    name = _name()
    response = _create(
        client,
        name=name,
        converter_pipeline=[{"converter": "OCRConverter", "params": {}}],
    )

    assert response.status_code == 409, response.text
    assert "must be downloaded" in response.json()["detail"]
    assert _stored_names(client, [name]) == []


def test_create_rejects_unknown_step_keys(client):
    response = _create(
        client,
        converter_pipeline=[{"converter": "TextSplitter", "params": {}, "extra": True}],
    )

    assert response.status_code == 422, response.text


def test_batch_rejects_unknown_step_keys(client):
    response = _batch(
        client,
        [_file()],
        converter_pipeline=[{"converter": "TextSplitter", "params": {}, "extra": True}],
    )

    assert response.status_code == 422, response.text
