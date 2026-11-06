"""Tests for the atomic folder + documents batch creation endpoint."""

import json
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from DashAI.back.core.enums.status import DocumentStatus
from DashAI.back.dependencies.database.models import DataDocument
from DashAI.back.services.documents.document_batch_service import (
    DocumentBatchService,
    name_chunks,
)

TEXT_LOADER = "PlainTextDocumentDataLoader"


def _name(prefix: str = "doc") -> str:
    """Build a unique document or folder name.

    Parameters
    ----------
    prefix : str
        Word the random suffix is appended to.

    Returns
    -------
    str
        A name no other test in the module uses.
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _file(
    name: str = None,
    file_name: str = "notes.txt",
    dataloader: str = TEXT_LOADER,
    dataloader_params: dict = None,
) -> dict:
    """Build one entry of the batch ``files`` list.

    Parameters
    ----------
    name : str, optional
        Document name; a unique one when omitted.
    file_name : str
        Name of the file the client will upload.
    dataloader : str
        Loader component name.
    dataloader_params : dict, optional
        Loader parameters.

    Returns
    -------
    dict
        The file payload.
    """
    return {
        "name": name or _name(),
        "file_name": file_name,
        "dataloader": dataloader,
        "dataloader_params": dataloader_params or {},
    }


def _batch(client, files: list, folder_name: str = None):
    """Post a batch request.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        The API client.
    files : list of dict
        The files to create.
    folder_name : str, optional
        Folder to create with them; omitted from the body when None.

    Returns
    -------
    httpx.Response
        The response.
    """
    payload = {"files": files}
    if folder_name is not None:
        payload["folder_name"] = folder_name
    return client.post("/api/v1/documents/batch", json=payload)


def _create_folder(client, name: str) -> dict:
    """Create a folder through the folders API.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        The API client.
    name : str
        Folder name.

    Returns
    -------
    dict
        The created folder.
    """
    response = client.post("/api/v1/folder/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _stored_names(client, names: list) -> list:
    """Return which of the given document names exist in the database.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        The API client.
    names : list of str
        Document names to look up.

    Returns
    -------
    list of str
        The names that were stored.
    """
    with client.app.container["session_factory"]() as db:
        return list(
            db.execute(
                select(DataDocument.name).where(DataDocument.name.in_(names))
            ).scalars()
        )


def test_batch_creates_the_folder_and_its_documents(client):
    folder_name = _name("folder")
    files = [_file() for _ in range(2)]

    response = _batch(client, files, folder_name)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["folder"]["name"] == folder_name
    folder_id = body["folder"]["id"]
    assert [row["name"] for row in body["documents"]] == [f["name"] for f in files]
    assert [row["folder_id"] for row in body["documents"]] == [folder_id, folder_id]
    assert all(
        row["status"] == DocumentStatus.NOT_STARTED.value for row in body["documents"]
    )
    listed = client.get("/api/v1/folder/").json()
    assert folder_id in [folder["id"] for folder in listed]
    with client.app.container["session_factory"]() as db:
        for row in body["documents"]:
            assert db.get(DataDocument, row["id"]).folder_id == folder_id


def test_batch_without_folder_creates_loose_documents(client):
    files = [_file(), _file()]

    response = _batch(client, files)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["folder"] is None
    assert [row["folder_id"] for row in body["documents"]] == [None, None]


def test_batch_documents_parse_through_the_job_endpoint(client):
    folder_name = _name("folder")
    contents = {
        "cap1.txt": b"One.\n\nTwo.",
        "cap2.txt": b"Three.\n\nFour.",
    }
    files = [
        _file(file_name=file_name, dataloader_params={"split_paragraphs": True})
        for file_name in contents
    ]

    created = _batch(client, files, folder_name)

    assert created.status_code == 201, created.text
    folder_id = created.json()["folder"]["id"]
    document_ids = [row["id"] for row in created.json()["documents"]]
    for document_id, (file_name, content) in zip(
        document_ids, contents.items(), strict=True
    ):
        enqueued = client.post(
            "/api/v1/job/",
            data={
                "job_type": "DocumentJob",
                "kwargs": json.dumps({"document_id": document_id}),
            },
            files={"file": (file_name, content, "application/octet-stream")},
            headers={"filename": file_name},
        )
        assert enqueued.status_code == 201, enqueued.text
    documents = [
        client.get(f"/api/v1/documents/{document_id}").json()
        for document_id in document_ids
    ]
    for document in documents:
        assert document["status"] == DocumentStatus.FINISHED.value
        assert document["content_counts"] == {"Text": 2}
        assert document["folder_id"] == folder_id
        assert Path(document["file_path"], "document").is_dir()


def test_batch_rejects_a_taken_folder_and_creates_no_documents(client):
    folder_name = _name("folder")
    _create_folder(client, folder_name)
    names = [_name()]

    response = _batch(client, [_file(name=name) for name in names], folder_name)

    assert response.status_code == 409, response.text
    assert _stored_names(client, names) == []


def test_batch_rejects_a_taken_document_name_and_creates_no_folder(client):
    folder_name = _name("folder")
    taken = _file()
    assert client.post("/api/v1/documents/", json=taken).status_code == 201
    names = [taken["name"], _name()]

    response = _batch(client, [_file(name=name) for name in names], folder_name)

    assert response.status_code == 409, response.text
    assert folder_name not in [f["name"] for f in client.get("/api/v1/folder/").json()]
    assert _stored_names(client, names) == [taken["name"]]


def test_batch_rejects_duplicate_names_within_the_batch(client):
    repeated = _name()
    files = [_file(name=repeated), _file(name=repeated)]

    response = _batch(client, files, _name("folder"))

    assert response.status_code == 409, response.text
    assert _stored_names(client, [repeated]) == []


def test_batch_rejects_an_unsupported_extension_atomically(client):
    valid = _file()
    files = [valid, _file(file_name="paper.pdf")]

    response = _batch(client, files, _name("folder"))

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_an_unknown_loader_atomically(client):
    valid = _file()
    files = [valid, _file(dataloader="NopeLoader")]

    response = _batch(client, files, _name("folder"))

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_a_dataset_loader_atomically(client):
    valid = _file()
    files = [valid, _file(file_name="iris.csv", dataloader="CSVDataLoader")]

    response = _batch(client, files, _name("folder"))

    assert response.status_code == 422, response.text
    assert "loads datasets, not documents" in response.json()["detail"]
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_an_empty_file_list(client):
    response = _batch(client, [])

    assert response.status_code == 422


def test_batch_rejects_an_empty_document_name_atomically(client):
    valid = _file()

    response = _batch(client, [valid, _file(name="   ")], _name("folder"))

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_an_empty_folder_name(client):
    for folder_name in ("", "   "):
        valid = _file()

        response = _batch(client, [valid], folder_name)

        assert response.status_code == 422, response.text
        assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_a_folder_name_that_collides_after_stripping(client):
    folder_name = _name("folder")
    _create_folder(client, folder_name)
    valid = _file()

    response = _batch(client, [valid], f"  {folder_name}  ")

    assert response.status_code == 409, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_keeps_only_the_base_name_of_each_file(client):
    response = _batch(client, [_file(file_name="../../etc/notes.txt")])

    assert response.status_code == 201, response.text
    assert response.json()["documents"][0]["file_name"] == "notes.txt"


def test_batch_accepts_more_than_one_hundred_files(client):
    files = [_file() for _ in range(101)]

    response = _batch(client, files, _name("folder"))

    assert response.status_code == 201, response.text
    assert len(response.json()["documents"]) == 101


def test_name_chunks_bounds_every_lookup():
    names = [f"doc_{index}" for index in range(1200)]

    chunks = list(name_chunks(names, size=500))

    assert [len(chunk) for chunk in chunks] == [500, 500, 200]
    assert [name for chunk in chunks for name in chunk] == names


def test_batch_looks_names_up_in_bounded_chunks(client):
    folder_name = _name("folder")
    files = [_file() for _ in range(1200)]

    response = _batch(client, files, folder_name)

    assert response.status_code == 201, response.text
    assert len(response.json()["documents"]) == 1200


def test_batch_maps_a_folder_race_to_a_conflict(client, monkeypatch):
    folder_name = _name("folder")
    _create_folder(client, folder_name)
    monkeypatch.setattr(
        DocumentBatchService, "_ensure_names_free", lambda *args, **kwargs: None
    )
    valid = _file()

    response = _batch(client, [valid], folder_name)

    assert response.status_code == 409, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_unknown_keys(client):
    response = client.post(
        "/api/v1/documents/batch",
        json={"folder": _name("folder"), "files": [_file()]},
    )

    assert response.status_code == 422, response.text


def test_batch_rejects_unknown_keys_inside_a_file(client):
    response = _batch(
        client,
        [{**_file(), "folder_id": 1}],
    )

    assert response.status_code == 422, response.text


def test_create_rejects_unknown_keys(client):
    response = client.post(
        "/api/v1/documents/", json={**_file(), "folder": _name("folder")}
    )

    assert response.status_code == 422, response.text


def test_batch_rejects_an_invisible_document_name(client):
    valid = _file()

    response = _batch(client, [valid, _file(name="\u200b")], _name("folder"))

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_batch_rejects_an_invisible_folder_name(client):
    valid = _file()

    response = _batch(client, [valid], "\u200b")

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_create_rejects_an_invisible_name(client):
    response = client.post("/api/v1/documents/", json=_file(name="\u200b"))

    assert response.status_code == 422, response.text


def test_create_rejects_a_boolean_folder_id(client):
    response = client.post("/api/v1/documents/", json={**_file(), "folder_id": True})

    assert response.status_code == 422, response.text


def test_create_rejects_a_string_folder_id(client):
    response = client.post("/api/v1/documents/", json={**_file(), "folder_id": "1"})

    assert response.status_code == 422, response.text


def test_batch_checks_the_extension_before_the_download_gate(client):
    config = client.app.container._services["config"]
    model_dir = Path(config["COMPONENT_PATH"]) / "UnstructuredDocumentDataLoader"
    shutil.rmtree(model_dir, ignore_errors=True)
    try:
        unsupported = _batch(
            client,
            [
                _file(
                    file_name="notes.xyz",
                    dataloader="UnstructuredDocumentDataLoader",
                )
            ],
            _name("folder"),
        )
        assert unsupported.status_code == 422, unsupported.text
        assert "accepts" in unsupported.json()["detail"]

        downloadable = _batch(
            client,
            [
                _file(
                    file_name="notes.docx", dataloader="UnstructuredDocumentDataLoader"
                )
            ],
            _name("folder"),
        )
        assert downloadable.status_code == 409, downloadable.text
        assert "must be downloaded" in downloadable.json()["detail"]
    finally:
        (model_dir / "en_core_web_sm").mkdir(parents=True, exist_ok=True)
        (model_dir / "en_core_web_sm" / "__init__.py").write_text("", encoding="utf-8")
        (model_dir / "en_core_web_sm-3.8.0.dist-info").mkdir(exist_ok=True)


def test_batch_rejects_a_name_longer_than_255_characters(client):
    response = _batch(client, [_file(name="n" * 256)], _name("folder"))

    assert response.status_code == 422, response.text


def test_batch_rejects_a_folder_name_longer_than_255_characters(client):
    valid = _file()

    response = _batch(client, [valid], "f" * 256)

    assert response.status_code == 422, response.text
    assert _stored_names(client, [valid["name"]]) == []


def test_create_accepts_a_name_of_255_characters(client):
    response = client.post("/api/v1/documents/", json=_file(name="n" * 255))

    assert response.status_code == 201, response.text
    assert len(response.json()["name"]) == 255


def test_create_assigns_the_given_folder(client):
    folder = _create_folder(client, _name("folder"))

    response = client.post(
        "/api/v1/documents/", json={**_file(), "folder_id": folder["id"]}
    )

    assert response.status_code == 201, response.text
    assert response.json()["folder_id"] == folder["id"]


def test_create_rejects_an_unknown_folder(client):
    response = client.post("/api/v1/documents/", json={**_file(), "folder_id": 999999})

    assert response.status_code == 404, response.text


def test_create_checks_the_folder_before_the_loader(client):
    response = client.post(
        "/api/v1/documents/",
        json={**_file(dataloader="NopeLoader"), "folder_id": 999999},
    )

    assert response.status_code == 404, response.text
