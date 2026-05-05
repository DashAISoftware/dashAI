"""Tests for BaseDatasetSource and DatasetEntry."""
import pytest
from DashAI.back.dataset_sources.base_dataset_source import DatasetEntry, BaseDatasetSource


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

    def fetch_preview(self, dataset_id, n_rows=100):
        import pandas as pd
        return pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})

    def fetch_full(self, dataset_id, temp_path):
        return ("/tmp/file.csv", "CSVDataLoader")

    def get_download_url(self, dataset_id):
        return f"https://example.com/download/{dataset_id}"


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


def test_concrete_source_fetch_preview_returns_dataframe():
    import pandas as pd
    source = ConcreteSource()
    df = source.fetch_preview("test/dataset", n_rows=2)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["col_a", "col_b"]


def test_concrete_source_fetch_full_returns_path_and_dataloader():
    source = ConcreteSource()
    path, dataloader_name = source.fetch_full("test/dataset", "/tmp")
    assert path == "/tmp/file.csv"
    assert dataloader_name == "CSVDataLoader"


def test_concrete_source_get_download_url():
    source = ConcreteSource()
    url = source.get_download_url("owner/name")
    assert url == "https://example.com/download/owner/name"


def test_incomplete_subclass_cannot_be_instantiated():
    from abc import ABC
    class Incomplete(BaseDatasetSource, ABC):
        pass
    with pytest.raises(TypeError):
        Incomplete()


from unittest.mock import patch, MagicMock
from DashAI.back.dataset_sources.huggingface_dataset_source import HuggingFaceDatasetSource


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


def test_hf_search_handles_http_error(caplog):
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        results = source.search("anything")

    assert results == []


def test_hf_get_download_url():
    source = HuggingFaceDatasetSource()
    url = source.get_download_url("owner/dataset")
    assert url == "https://huggingface.co/datasets/owner/dataset"


def test_hf_fetch_preview_returns_dataframe():
    import pandas as pd

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "features": [{"name": "text"}, {"name": "label"}],
        "rows": [
            {"row": {"text": "good movie", "label": 1}},
            {"row": {"text": "bad movie", "label": 0}},
        ],
    }

    with patch("httpx.get", return_value=mock_response):
        source = HuggingFaceDatasetSource()
        df = source.fetch_preview("stanfordnlp/imdb", n_rows=2)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["text", "label"]
    assert len(df) == 2
