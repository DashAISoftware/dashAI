"""Tests for document extractors."""

import pytest

from DashAI.back.models.RAG.exceptions import RAGDocumentParsingError
from DashAI.back.models.RAG.extractors.base_extractor import BaseExtractor
from DashAI.back.models.RAG.extractors.plain_text_extractor import PlainTextExtractor
from DashAI.back.models.RAG.extractors.pypdf2_extractor import PypdfExtractor


class TestBaseExtractor:
    def test_type_is_extractor(self):
        assert BaseExtractor.TYPE == "Extractor"

    def test_supported_file_types_default_empty(self):
        assert BaseExtractor.SUPPORTED_FILE_TYPES == []

    def test_get_metadata_returns_supported_types(self):
        class DummyExtractor(BaseExtractor):
            SUPPORTED_FILE_TYPES = ["pdf"]

            def extract(self, file_path):
                return "dummy"

        metadata = DummyExtractor.get_metadata()
        assert metadata["supported_file_types"] == ["pdf"]

    def test_config_object_inheritance(self):
        """BaseExtractor inherits from ConfigObject."""
        from DashAI.back.config_object import ConfigObject

        assert issubclass(BaseExtractor, ConfigObject)


class TestPlainTextExtractor:
    def test_supported_file_types(self):
        assert set(PlainTextExtractor.SUPPORTED_FILE_TYPES) >= {
            "txt",
            "md",
            "rst",
            "tex",
            "csv",
        }

    def test_extract_txt(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello world\n\nThis is a test.", encoding="utf-8")
        extractor = PlainTextExtractor()
        text = extractor.extract(str(file_path))
        assert text == "Hello world\n\nThis is a test."

    def test_extract_file_not_found(self):
        extractor = PlainTextExtractor()
        with pytest.raises(RAGDocumentParsingError, match="File not found"):
            extractor.extract("/nonexistent/path.txt")


class TestPypdfExtractor:
    def test_supported_file_types(self):
        assert PypdfExtractor.SUPPORTED_FILE_TYPES == ["pdf"]

    def test_get_metadata(self):
        metadata = PypdfExtractor.get_metadata()
        assert metadata["supported_file_types"] == ["pdf"]


class TestExtractorSchemaRegistration:
    """Verify extractors are properly registered in the component registry."""

    def test_extractors_registered(self, client):
        """Remaining extractors appear in the registry under Extractor type."""
        resp = client.get("/api/v1/component/?type=Extractor")
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()}
        assert {"PypdfExtractor", "PlainTextExtractor"}.issubset(names)

    def test_removed_extractors_absent(self, client):
        """PyMuPDF and EasyOCR extractors are gone from the registry."""
        resp = client.get("/api/v1/component/?type=Extractor")
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()}
        assert "PyMuPDFExtractor" not in names
        assert "EasyOCRExtractor" not in names

    def test_get_child_components(self, client):
        """getChildComponents('BaseExtractor', false) returns all extractors."""
        resp = client.get("/api/v1/component/BaseExtractor/children?recursive=false")
        assert resp.status_code == 200
        components = resp.json()
        names = {c["name"] for c in components}
        expected = {
            "PypdfExtractor",
            "PlainTextExtractor",
        }
        assert expected.issubset(names)

    def test_pypdf_metadata_has_supported_types(self, client):
        """Registry metadata includes supported_file_types for frontend filtering."""
        resp = client.get("/api/v1/component/?type=Extractor")
        assert resp.status_code == 200
        pypdf_entry = next(
            (c for c in resp.json() if c["name"] == "PypdfExtractor"), None
        )
        assert pypdf_entry is not None
        assert pypdf_entry["metadata"]["supported_file_types"] == ["pdf"]


class TestPlainTextExtractorParams:
    def test_default_encoding(self):
        from DashAI.back.models.RAG.extractors.plain_text_extractor import (
            PlainTextExtractor,
        )

        ext = PlainTextExtractor()
        assert ext.encoding == "utf-8"

    def test_custom_encoding(self):
        from DashAI.back.models.RAG.extractors.plain_text_extractor import (
            PlainTextExtractor,
        )

        ext = PlainTextExtractor(encoding="latin-1")
        assert ext.encoding == "latin-1"

    def test_schema_has_encoding(self):
        from DashAI.back.models.RAG.extractors.plain_text_extractor import (
            PlainTextExtractor,
        )

        schema = PlainTextExtractor.get_schema()
        assert "encoding" in schema["properties"]


class TestPypdfExtractorParams:
    def test_default_strict(self):
        from DashAI.back.models.RAG.extractors.pypdf2_extractor import PypdfExtractor

        ext = PypdfExtractor()
        assert ext.strict is True

    def test_lenient_mode(self):
        from DashAI.back.models.RAG.extractors.pypdf2_extractor import PypdfExtractor

        ext = PypdfExtractor(strict=False)
        assert ext.strict is False

    def test_schema_has_strict(self):
        from DashAI.back.models.RAG.extractors.pypdf2_extractor import PypdfExtractor

        schema = PypdfExtractor.get_schema()
        assert "strict" in schema["properties"]
