"""Integration tests for document extraction with processed_document_content cache.

Verifies the full flow across txt, md, and pdf file types:
extraction → cache hit/miss → signature invalidation when extractor config changes.
"""

import os
import tempfile
import uuid

import pytest

from DashAI.back.dependencies.database.models import Document, RAGExtractor

_EXTRACTOR_BY_FILE_TYPE = {
    "pdf": "PyMuPDFExtractor",
    "txt": "PlainTextExtractor",
    "md": "PlainTextExtractor",
}


def _make_minimal_pdf(path: str) -> None:
    """Write a minimal valid PDF file to the given path."""
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"  # noqa: E501
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"  # noqa: E501
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )
    with open(path, "wb") as f:
        f.write(content)


def _create_document(client, file_type: str, content: bytes | str) -> int:
    """Create a document in the DB and return its id."""
    session_factory = client.app.container["session_factory"]
    unique_hash = f"cache_flow_{file_type}_{uuid.uuid4().hex[:12]}"
    ext = "pdf" if file_type == "pdf" else file_type

    tmp_path = os.path.join(
        tempfile.gettempdir(), f"test_extract_cache_{file_type}_{unique_hash}.{ext}"
    )

    if file_type == "pdf":
        _make_minimal_pdf(tmp_path)
    else:
        mode = "w" if isinstance(content, str) else "wb"
        with open(tmp_path, mode, encoding="utf-8" if mode == "w" else None) as f:
            f.write(content)

    with session_factory() as db:
        extractor = RAGExtractor(
            component_name=_EXTRACTOR_BY_FILE_TYPE[file_type], params={}
        )
        db.add(extractor)
        db.flush()
        doc = Document(
            file_name=f"test_cache.{ext}",
            file_type=file_type,
            file_path=tmp_path,
            file_hash=unique_hash,
            extractor_id=extractor.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id


class TestExtractionCacheFlowTxt:
    """Cache flow tests for .txt files."""

    @pytest.fixture(autouse=True)
    def _setup(self, client):
        self.doc_id = _create_document(
            client, "txt", "Hello from DashAI txt extraction cache test."
        )

    def test_first_extraction_cache_miss(self, client):
        resp = client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert "Hello from DashAI txt" in data["text"]

    def test_second_extraction_cache_hit(self, client):
        client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        resp = client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        assert resp.status_code == 200
        assert resp.json()["cached"] is True

    def test_different_params_cache_miss(self, client):
        client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        resp = client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={
                "extractor": {
                    "component": "PlainTextExtractor",
                    "params": {"encoding": "latin-1"},
                }
            },
        )
        assert resp.status_code == 200
        assert resp.json()["cached"] is False

    def test_two_entries_persisted(self, client):
        client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={
                "extractor": {
                    "component": "PlainTextExtractor",
                    "params": {"encoding": "latin-1"},
                }
            },
        )
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            from DashAI.back.dependencies.database.models import (
                ProcessedDocumentContent,
            )

            entries = (
                db.query(ProcessedDocumentContent)
                .filter_by(document_id=self.doc_id)
                .all()
            )
            assert len(entries) == 2
            assert len({e.signature for e in entries}) == 2

    def test_cascade_on_delete(self, client):
        client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        session_factory = client.app.container["session_factory"]

        with session_factory() as db:
            from DashAI.back.dependencies.database.models import (
                ProcessedDocumentContent,
            )

            assert (
                db.query(ProcessedDocumentContent)
                .filter_by(document_id=self.doc_id)
                .count()
                >= 1
            )

        resp = client.delete(f"/api/v1/document/{self.doc_id}")
        assert resp.status_code == 204

        with session_factory() as db:
            from DashAI.back.dependencies.database.models import (
                ProcessedDocumentContent,
            )

            assert (
                db.query(ProcessedDocumentContent)
                .filter_by(document_id=self.doc_id)
                .count()
                == 0
            )


class TestExtractionCacheFlowMd:
    """Cache flow tests for .md files (plain text, same extractor as txt)."""

    @pytest.fixture(autouse=True)
    def _setup(self, client):
        self.doc_id = _create_document(
            client, "md", "# DashAI\n\nMarkdown extraction cache test."
        )

    def test_first_extraction_cache_miss(self, client):
        resp = client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert "Markdown extraction cache test" in data["text"]

    def test_second_extraction_cache_hit(self, client):
        client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        resp = client.post(f"/api/v1/document/{self.doc_id}/extract", json={})
        assert resp.status_code == 200
        assert resp.json()["cached"] is True


class TestExtractionCacheFlowPdf:
    """Cache flow tests for .pdf files across all PDF extractors."""

    @pytest.fixture(autouse=True)
    def _setup(self, client):
        self.doc_id = _create_document(client, "pdf", b"")

    # ── PypdfExtractor ──

    def test_pypdf2_cache_hit(self, client):
        """PypdfExtractor: cache hit on second extraction."""
        extractor = {"component": "PypdfExtractor", "params": {"strict": False}}
        client.post(
            f"/api/v1/document/{self.doc_id}/extract", json={"extractor": extractor}
        )
        resp = client.post(
            f"/api/v1/document/{self.doc_id}/extract", json={"extractor": extractor}
        )
        assert resp.status_code == 200
        assert resp.json()["cached"] is True

    def test_pypdf2_different_params(self, client):
        """PyMuPDF: different params -> cache miss (no password vs with password)."""
        client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={"extractor": {"component": "PyMuPDFExtractor", "params": {}}},
        )
        resp = client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={
                "extractor": {
                    "component": "PyMuPDFExtractor",
                    "params": {"password": "test"},
                }
            },
        )
        assert resp.status_code == 200
        assert resp.json()["cached"] is False

    # ── PyMuPDFExtractor ──

    def test_pymupdf_extracts(self, client):
        """PyMuPDFExtractor: should extract from a minimal PDF."""
        resp = client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={"extractor": {"component": "PyMuPDFExtractor", "params": {}}},
        )
        assert resp.status_code == 200
        assert "text" in resp.json()
        assert resp.json()["cached"] is False

    def test_pymupdf_cache_hit(self, client):
        """PyMuPDFExtractor: cache hit on second extraction."""
        extractor = {"component": "PyMuPDFExtractor", "params": {}}
        client.post(
            f"/api/v1/document/{self.doc_id}/extract", json={"extractor": extractor}
        )
        resp = client.post(
            f"/api/v1/document/{self.doc_id}/extract", json={"extractor": extractor}
        )
        assert resp.status_code == 200
        assert resp.json()["cached"] is True

    # ── Cross-extractor: different extractors produce different signatures ──

    def test_different_extractors_different_cache(self, client):
        """Different PDF extractors → different signatures → separate cache entries."""
        resp_a = client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={
                "extractor": {
                    "component": "PypdfExtractor",
                    "params": {"strict": False},
                }
            },
        )
        resp_b = client.post(
            f"/api/v1/document/{self.doc_id}/extract",
            json={"extractor": {"component": "PyMuPDFExtractor", "params": {}}},
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["cached"] is False
        assert resp_b.json()["cached"] is False

        # Verify two distinct cache entries
        session_factory = client.app.container["session_factory"]
        with session_factory() as db:
            from DashAI.back.dependencies.database.models import (
                ProcessedDocumentContent,
            )

            entries = (
                db.query(ProcessedDocumentContent)
                .filter_by(document_id=self.doc_id)
                .all()
            )
            assert len(entries) == 2
            assert len({e.signature for e in entries}) == 2

    # ── Incompatible extractor ──

    def test_pdf_extractor_rejected_for_txt(self, client):
        """PDF extractors should be rejected for non-PDF files."""
        txt_id = _create_document(
            client, "txt", "txt content for incompatibility test."
        )
        for component in ("PypdfExtractor", "PyMuPDFExtractor"):
            resp = client.post(
                f"/api/v1/document/{txt_id}/extract",
                json={"extractor": {"component": component, "params": {}}},
            )
            assert resp.status_code == 400, (
                f"{component}: expected 400, got {resp.status_code}"
            )
            assert "does not support" in resp.json()["detail"]
