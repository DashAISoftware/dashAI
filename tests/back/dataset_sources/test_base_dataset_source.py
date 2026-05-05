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
