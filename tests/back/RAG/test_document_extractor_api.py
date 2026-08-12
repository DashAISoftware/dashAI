"""Tests for the document extractor API endpoints."""

import os
import tempfile

from DashAI.back.dependencies.database.models import Document, RAGExtractor


def _create_document(
    db, file_name: str, file_hash: str, content: str = "content"
) -> int:
    """Create a txt test document (with extractor) in the DB and return its ID."""
    tmp_path = os.path.join(tempfile.gettempdir(), file_name)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    extractor = RAGExtractor(component_name="PlainTextExtractor", params={})
    db.add(extractor)
    db.flush()
    doc = Document(
        file_name=file_name,
        file_type="txt",
        file_path=tmp_path,
        file_hash=file_hash,
        extractor_id=extractor.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc.id


class TestExtractEndpoint:
    """Tests for POST /api/v1/document/{id}/extract."""

    def test_extract_with_stored_extractor(self, client):
        """Extract text using the document's stored/default extractor."""
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            doc_id = _create_document(
                db,
                "test_extract_doc.txt",
                "extract_test_hash_001",
                "Test content for extraction.",
            )

        resp = client.post(f"/api/v1/document/{doc_id}/extract", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "extractor" in data
        assert "char_count" in data
        assert data["text"] == "Test content for extraction."

    def test_extract_with_specific_extractor(self, client):
        """Extract text using a specific extractor by name."""
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            doc_id = _create_document(
                db,
                "test_extract_specific.txt",
                "extract_specific_hash_002",
                "Plain text extracted.",
            )

        resp = client.post(
            f"/api/v1/document/{doc_id}/extract",
            json={"extractor": {"component": "PlainTextExtractor", "params": {}}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Plain text extracted."
        assert data["extractor"]["component"] == "PlainTextExtractor"

    def test_extract_incompatible_extractor(self, client):
        """Using an extractor incompatible with the file type returns 400."""
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            doc_id = _create_document(
                db, "test_incompat.txt", "incompat_hash_003", "text content"
            )

        # PDF extractors should not work with txt files
        resp = client.post(
            f"/api/v1/document/{doc_id}/extract",
            json={"extractor": {"component": "PyMuPDFExtractor", "params": {}}},
        )
        assert resp.status_code == 400
        assert "does not support" in resp.json()["detail"]

    def test_extract_document_not_found(self, client):
        resp = client.post("/api/v1/document/99999/extract", json={})
        assert resp.status_code == 404


class TestUpdateExtractorEndpoint:
    """Tests for PUT /api/v1/document/{id}/extractor."""

    def test_update_without_pipelines(self, client):
        """Update extractor for a document not linked to any pipeline."""
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            doc_id = _create_document(db, "test_update_ext.txt", "update_ext_hash_010")

        resp = client.put(
            f"/api/v1/document/{doc_id}/extractor",
            json={
                "extractor": {"component": "PlainTextExtractor", "params": {}},
                "force": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["extractor"]["component"] == "PlainTextExtractor"

    def test_update_invalid_component(self, client):
        """Using a non-existent extractor name returns 400."""
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            doc_id = _create_document(
                db, "test_invalid_comp.txt", "invalid_comp_hash_012"
            )

        resp = client.put(
            f"/api/v1/document/{doc_id}/extractor",
            json={"extractor": {"component": "NonExistentExtractor", "params": {}}},
        )
        assert resp.status_code == 400

    def test_update_document_not_found(self, client):
        resp = client.put(
            "/api/v1/document/99999/extractor",
            json={"extractor": {"component": "PlainTextExtractor", "params": {}}},
        )
        assert resp.status_code == 404
