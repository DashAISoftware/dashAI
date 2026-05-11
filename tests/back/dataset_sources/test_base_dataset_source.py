"""Tests for BaseDatasetSource and DatasetEntry."""

from unittest.mock import MagicMock, patch

import pytest

from DashAI.back.dataset_sources.base_dataset_source import (
    BaseDatasetSource,
    DatasetEntry,
)
from DashAI.back.dataset_sources.huggingface_dataset_source import (
    HuggingFaceDatasetSource,
)
from DashAI.back.dataset_sources.openml_dataset_source import OpenMLDatasetSource


class ConcreteSource(BaseDatasetSource):
    DISPLAY_NAME = "Test Source"
    DESCRIPTION = "A test source"

    def search(self, query, limit=20, **filters):
        return [
            DatasetEntry(
                id="test/dataset",
                name="Test Dataset",
                description="A test dataset",
                tags=["tabular"],
                size_bytes=1024,
                row_count=100,
                url="https://example.com/test",
                source="ConcreteSource",
            )
        ]

    def download_dataset(self, dataset_id, temp_path):
        return "/tmp/file.csv"


def test_dataset_entry_fields():
    entry = DatasetEntry(
        id="owner/name",
        name="My Dataset",
        description="desc",
        tags=["nlp"],
        size_bytes=2048,
        row_count=500,
        url="https://example.com",
        source="HuggingFaceDatasetSource",
    )
    assert entry.id == "owner/name"
    assert entry.name == "My Dataset"
    assert entry.tags == ["nlp"]
    assert entry.source == "HuggingFaceDatasetSource"


def test_dataset_entry_optional_fields():
    entry = DatasetEntry(
        id="x",
        name="x",
        description="",
        tags=[],
        size_bytes=None,
        row_count=None,
        url="",
        source="",
    )
    assert entry.size_bytes is None
    assert entry.row_count is None


def test_concrete_source_has_type():
    assert ConcreteSource.TYPE == "DatasetSource"


def test_concrete_source_search_returns_entries():
    source = ConcreteSource()
    results = source.search("test")
    assert len(results) == 1
    assert isinstance(results[0], DatasetEntry)
    assert results[0].id == "test/dataset"


def test_concrete_source_download_dataset_returns_path():
    source = ConcreteSource()
    path = source.download_dataset("test/dataset", "/tmp")
    assert path == "/tmp/file.csv"


def test_incomplete_subclass_cannot_be_instantiated():
    from abc import ABC

    class Incomplete(BaseDatasetSource, ABC):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_hf_source_has_correct_type():
    assert HuggingFaceDatasetSource.TYPE == "DatasetSource"


def test_hf_search_returns_dataset_entries():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "stanfordnlp/imdb",
            "description": "IMDB movie review sentiment",
            "tags": ["text-classification"],
            "cardData": {"size_categories": ["10K<n<100K"]},
            "usedStorage": 5242880,
            "downloads": 5000,
        }
    ]

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        results = source.search("imdb", limit=5)

    assert len(results) == 1
    assert results[0].id == "stanfordnlp/imdb"
    assert results[0].source == "HuggingFaceDatasetSource"
    assert results[0].url == "https://huggingface.co/datasets/stanfordnlp/imdb"
    assert results[0].size_bytes == 5242880


def test_hf_search_size_bytes_none_when_missing():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": "owner/repo",
            "description": "",
            "tags": [],
        }
    ]

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        results = source.search("repo")

    assert results[0].size_bytes is None


def test_hf_search_handles_http_error(caplog):
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        results = source.search("anything")

    assert results == []


def test_openml_source_has_correct_type():
    assert OpenMLDatasetSource.TYPE == "DatasetSource"


def test_openml_search_returns_dataset_entries():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hits": {
            "total": 1,
            "hits": [
                {
                    "_id": "61",
                    "_source": {
                        "data_id": 61,
                        "name": "iris",
                        "description": "Iris flower dataset.",
                        "qualities": {"NumberOfInstances": 150},
                        "file_size": 25000,
                        "tag": ["study_14", "uci"],
                    },
                }
            ],
        }
    }

    with patch("httpx.post", return_value=mock_resp):
        source = OpenMLDatasetSource()
        results = source.search("iris", limit=5)

    assert len(results) == 1
    assert results[0].id == "61"
    assert results[0].name == "iris"
    assert results[0].row_count == 150
    assert results[0].size_bytes == 25000
    assert results[0].description == "Iris flower dataset."
    assert results[0].tags == ["study_14", "uci"]
    assert results[0].source == "OpenMLDatasetSource"
    assert results[0].url == "https://www.openml.org/d/61"


def test_openml_search_size_bytes_none_when_missing():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "1",
                    "_source": {
                        "data_id": 1,
                        "name": "no-size",
                        "description": "",
                        "qualities": {},
                        "tag": [],
                    },
                }
            ]
        }
    }

    with patch("httpx.post", return_value=mock_resp):
        source = OpenMLDatasetSource()
        results = source.search("no-size")

    assert results[0].size_bytes is None


def test_openml_search_empty_query_uses_match_all():
    """Empty query should use match_all (not multi_match) in ES body."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hits": {"total": 0, "hits": []}}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        source = OpenMLDatasetSource()
        source.search("", limit=20, offset=0)

    sent_body = mock_post.call_args[1]["json"]
    must_clause = sent_body["query"]["bool"]["must"]
    assert "match_all" in must_clause
    assert "multi_match" not in must_clause


def test_openml_search_uses_from_for_pagination():
    """offset param maps to ES 'from' field for pagination."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hits": {"total": 0, "hits": []}}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        source = OpenMLDatasetSource()
        source.search("iris", limit=10, offset=20)

    sent_body = mock_post.call_args[1]["json"]
    assert sent_body["from"] == 20
    assert sent_body["size"] == 10


def test_openml_search_handles_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.post", return_value=mock_response):
        source = OpenMLDatasetSource()
        results = source.search("iris")

    assert results == []


def test_openml_get_info_returns_size_bytes():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data_set_description": {
            "description": "Iris flowers.",
            "tag": ["uci"],
            "file_size": 4608,
        }
    }

    with patch("httpx.get", return_value=mock_resp):
        source = OpenMLDatasetSource()
        entry = source.get_info("61")

    assert entry is not None
    assert entry.size_bytes == 4608


def test_openml_download_dataset_returns_arff(tmp_path):
    info_response = MagicMock()
    info_response.status_code = 200
    info_response.json.return_value = {
        "data_set_description": {
            "file_id": "22044555",
            "url": "https://openml.org/data/v1/download/22044555/iris.arff",
        }
    }

    arff_content = b"""@relation iris
@attribute sepalLength numeric
@attribute class {Iris-setosa,Iris-versicolor}
@data
5.1,Iris-setosa
4.9,Iris-versicolor
"""
    file_response = MagicMock()
    file_response.status_code = 200
    file_response.content = arff_content
    file_response.raise_for_status = MagicMock()

    info_response.raise_for_status = MagicMock()

    with patch("httpx.get", side_effect=[info_response, file_response]):
        source = OpenMLDatasetSource()
        arff_path = source.download_dataset("61", str(tmp_path))

    assert arff_path.endswith(".arff")
    with open(arff_path, "rb") as fh:
        assert b"sepalLength" in fh.read()
