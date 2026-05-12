"""Tests for BaseDatasetSource and DatasetEntry."""

from unittest.mock import MagicMock, patch

import pytest

from DashAI.back.dataset_sources.base_dataset_source import (
    BaseDatasetSource,
    DatasetEntry,
    SearchPage,
)
from DashAI.back.dataset_sources.huggingface_dataset_source import (
    HuggingFaceDatasetSource,
)
from DashAI.back.dataset_sources.openml_dataset_source import OpenMLDatasetSource


class ConcreteSource(BaseDatasetSource):
    DISPLAY_NAME = "Test Source"
    DESCRIPTION = "A test source"

    def search(self, query, limit=20, cursor=None, **filters):
        return SearchPage(
            entries=[
                DatasetEntry(
                    id="test/dataset",
                    name="Test Dataset",
                    description="A test dataset",
                    tags=["tabular"],
                    size_bytes=1024,
                    url="https://example.com/test",
                    source="ConcreteSource",
                )
            ],
            next_cursor=None,
        )

    def download_dataset(self, dataset_id, temp_path):
        return "/tmp/file.csv"


def test_dataset_entry_fields():
    entry = DatasetEntry(
        id="owner/name",
        name="My Dataset",
        description="desc",
        tags=["nlp"],
        size_bytes=2048,
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
        url="",
        source="",
    )
    assert entry.size_bytes is None


def test_concrete_source_has_type():
    assert ConcreteSource.TYPE == "DatasetSource"


def test_concrete_source_search_returns_entries():
    source = ConcreteSource()
    page = source.search("test")
    assert isinstance(page, SearchPage)
    assert len(page.entries) == 1
    assert isinstance(page.entries[0], DatasetEntry)
    assert page.entries[0].id == "test/dataset"
    assert page.next_cursor is None


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
    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.headers = {
        "Link": '<https://huggingface.co/api/datasets?cursor=abc123>; rel="next"'
    }
    search_resp.json.return_value = [
        {
            "id": "stanfordnlp/imdb",
            "description": "IMDB movie review sentiment",
            "tags": ["text-classification"],
        }
    ]

    with patch("httpx.get", return_value=search_resp):
        source = HuggingFaceDatasetSource()
        page = source.search("imdb", limit=5)

    assert isinstance(page, SearchPage)
    assert len(page.entries) == 1
    assert page.entries[0].id == "stanfordnlp/imdb"
    assert page.entries[0].source == "HuggingFaceDatasetSource"
    assert page.entries[0].url == "https://huggingface.co/datasets/stanfordnlp/imdb"
    assert page.entries[0].size_bytes is None
    assert page.next_cursor == "abc123"


def test_hf_get_info_returns_size_bytes():
    mock_item = MagicMock()
    mock_item.description = "IMDB movie review sentiment"
    mock_item.tags = ["text-classification"]
    mock_item.used_storage = 83455823

    with patch("huggingface_hub.HfApi") as MockApi:
        MockApi.return_value.dataset_info.return_value = mock_item
        source = HuggingFaceDatasetSource()
        entry = source.get_info("stanfordnlp/imdb")

    assert entry is not None
    assert entry.id == "stanfordnlp/imdb"
    assert entry.size_bytes == 83455823


def test_hf_get_info_returns_none_on_error():
    with patch("huggingface_hub.HfApi") as MockApi:
        MockApi.return_value.dataset_info.side_effect = Exception("not found")
        source = HuggingFaceDatasetSource()
        entry = source.get_info("owner/repo")

    assert entry is None


def test_hf_get_info_size_none_when_used_storage_absent():
    mock_item = MagicMock()
    mock_item.description = ""
    mock_item.tags = []
    mock_item.used_storage = None

    with patch("huggingface_hub.HfApi") as MockApi:
        MockApi.return_value.dataset_info.return_value = mock_item
        source = HuggingFaceDatasetSource()
        entry = source.get_info("owner/repo")

    assert entry is not None
    assert entry.size_bytes is None


def test_hf_search_uses_cursor_for_next_page():
    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.headers = {}
    search_resp.json.return_value = [
        {"id": "owner/repo", "description": "", "tags": []}
    ]

    with patch("httpx.get", return_value=search_resp) as mock_get:
        source = HuggingFaceDatasetSource()
        source.search("repo", cursor="prev_cursor")

    search_call_kwargs = mock_get.call_args_list[0][1]["params"]
    assert search_call_kwargs.get("cursor") == "prev_cursor"


def test_hf_search_size_bytes_none_when_card_data_absent():
    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.headers = {}
    search_resp.json.return_value = [
        {"id": "owner/repo", "description": "", "tags": []}
    ]

    with patch("httpx.get", return_value=search_resp):
        source = HuggingFaceDatasetSource()
        page = source.search("repo")

    assert page.entries[0].size_bytes is None
    assert page.next_cursor is None


def test_hf_search_handles_http_error(caplog):
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        page = source.search("anything")

    assert page.entries == []
    assert page.next_cursor is None


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
                        "tags": [
                            {"tag": "study_14", "uploader": "1"},
                            {"tag": "uci", "uploader": "1"},
                        ],
                    },
                }
            ],
        }
    }

    with patch("httpx.post", return_value=mock_resp):
        source = OpenMLDatasetSource()
        page = source.search("iris", limit=5)

    assert isinstance(page, SearchPage)
    assert len(page.entries) == 1
    assert page.entries[0].id == "61"
    assert page.entries[0].name == "iris"
    assert page.entries[0].size_bytes is None
    assert page.entries[0].description == "Iris flower dataset."
    assert page.entries[0].tags == ["study_14", "uci"]
    assert page.entries[0].source == "OpenMLDatasetSource"
    assert page.entries[0].url == "https://www.openml.org/d/61"
    assert page.next_cursor is None


def test_openml_search_empty_query_uses_match_all():
    """Empty query should use match_all (not multi_match) in ES body."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hits": {"total": 0, "hits": []}}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        source = OpenMLDatasetSource()
        source.search("", limit=20)

    sent_body = mock_post.call_args[1]["json"]
    must_clause = sent_body["query"]["bool"]["must"]
    assert "match_all" in must_clause
    assert "multi_match" not in must_clause


def test_openml_search_uses_cursor_for_pagination():
    """cursor string encodes numeric offset passed to ES 'from'."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"hits": {"total": 0, "hits": []}}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        source = OpenMLDatasetSource()
        source.search("iris", limit=10, cursor="20")

    sent_body = mock_post.call_args[1]["json"]
    assert sent_body["from"] == 20
    assert sent_body["size"] == 10


def test_openml_search_next_cursor_set_when_full_page():
    """next_cursor is non-null when a full page is returned."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": str(i),
                    "_source": {
                        "data_id": i,
                        "name": f"ds{i}",
                        "description": "",
                        "tags": [],
                    },
                }
                for i in range(5)
            ]
        }
    }

    with patch("httpx.post", return_value=mock_resp):
        source = OpenMLDatasetSource()
        page = source.search("x", limit=5)

    assert page.next_cursor == "5"


def test_openml_search_next_cursor_none_when_partial_page():
    """next_cursor is null when fewer results than limit are returned."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "1",
                    "_source": {
                        "data_id": 1,
                        "name": "only",
                        "description": "",
                        "tags": [],
                    },
                }
            ]
        }
    }

    with patch("httpx.post", return_value=mock_resp):
        source = OpenMLDatasetSource()
        page = source.search("x", limit=5)

    assert page.next_cursor is None


def test_openml_search_handles_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.post", return_value=mock_response):
        source = OpenMLDatasetSource()
        page = source.search("iris")

    assert page.entries == []
    assert page.next_cursor is None


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
