"""Regression test: a folder deleted while a document is filed into it.

SQLite runs here without foreign keys, so nothing in the database stops a
document from keeping a ``folder_id`` that points at a folder deleted between
the existence check and the INSERT. The service takes SQLite's write lock
before it reads the folder, which makes the delete wait and then detach the
document instead of leaving it dangling.
"""

import threading
import time
import uuid

from DashAI.back.dependencies.database.models import DataDocument, Folder
from DashAI.back.services.documents.document_batch_service import (
    DocumentBatchService,
)


def _folder(client) -> dict:
    """Create a folder to race against.

    Parameters
    ----------
    client : fastapi.testclient.TestClient
        The API client.

    Returns
    -------
    dict
        The created folder.
    """
    response = client.post(
        "/api/v1/folder/", json={"name": f"race_{uuid.uuid4().hex[:8]}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _document_payload(name: str, folder_id: int) -> dict:
    """Build a create-document body that files the document into a folder.

    Parameters
    ----------
    name : str
        Document name.
    folder_id : int
        Folder receiving it.

    Returns
    -------
    dict
        The request body.
    """
    return {
        "name": name,
        "file_name": "notes.txt",
        "dataloader": "PlainTextDocumentDataLoader",
        "dataloader_params": {},
        "folder_id": folder_id,
    }


def test_folder_delete_waits_for_a_document_being_filed(client, monkeypatch):
    folder = _folder(client)
    locked = threading.Event()
    original = DocumentBatchService._existing_folder

    def slow_existing_folder(db, folder_id):
        """Signal that the write lock is held, then behave normally."""
        locked.set()
        time.sleep(0.2)
        return original(db, folder_id)

    monkeypatch.setattr(
        DocumentBatchService, "_existing_folder", staticmethod(slow_existing_folder)
    )
    result = {}

    def delete_folder():
        """Delete the folder once the create request holds the lock."""
        if not locked.wait(timeout=10):
            return
        result["response"] = client.delete(f"/api/v1/folder/{folder['id']}")

    deleter = threading.Thread(target=delete_folder)
    deleter.start()
    try:
        created = client.post(
            "/api/v1/documents/",
            json=_document_payload(f"race_doc_{uuid.uuid4().hex[:8]}", folder["id"]),
        )
    finally:
        deleter.join(timeout=30)

    assert not deleter.is_alive(), "the folder delete never finished"
    assert "response" in result, "the folder delete never saw the lock"
    assert created.status_code == 201, created.text
    assert result["response"].status_code == 204, result["response"].text
    with client.app.container["session_factory"]() as db:
        assert db.get(Folder, folder["id"]) is None
        document = db.get(DataDocument, created.json()["id"])
        assert document.folder_id is None
        dangling = (
            db.query(DataDocument)
            .outerjoin(Folder, DataDocument.folder_id == Folder.id)
            .filter(DataDocument.folder_id.is_not(None), Folder.id.is_(None))
            .all()
        )
        assert dangling == []
