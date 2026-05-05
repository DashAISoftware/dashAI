"""Tests for the dataset_source API endpoints."""
import os
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dataset_sources.base_dataset_source import BaseDatasetSource, DatasetEntry
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader
from DashAI.back.dependencies.registry import ComponentRegistry


class MockDataLoader(BaseDataLoader):
    """Minimal DataLoader for testing the hub import path."""

    name = "MockDataLoader"

    @classmethod
    def get_schema(cls):
        return {}

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample=None,
    ):
        import pandas as pd

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        df = pd.read_csv(filepath_or_buffer)
        return to_dashai_dataset(df)


class MockDatasetSource(BaseDatasetSource):
    DISPLAY_NAME = "Mock Source"
    DESCRIPTION = "Mock for testing"

    def search(self, query, limit=20, **filters):
        if query == "error":
            return []
        return [
            DatasetEntry(
                id="mock/dataset",
                name="Mock Dataset",
                description="A mock dataset",
                tags=["tabular"],
                size_bytes=1024,
                row_count=100,
                url="https://mock.example.com/mock-dataset",
                source="MockDatasetSource",
            )
        ]

    def fetch_preview(self, dataset_id, n_rows=100):
        import pandas as pd
        return pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})

    def fetch_full(self, dataset_id, temp_path):
        csv_path = os.path.join(temp_path, "mock.csv")
        with open(csv_path, "w") as f:
            f.write("col_a,col_b\n1,x\n2,y\n3,z\n")
        return (csv_path, "MockDataLoader")

    def get_download_url(self, dataset_id):
        return f"https://mock.example.com/{dataset_id}"

    @classmethod
    def get_schema(cls):
        return {}


@pytest.fixture(autouse=True, name="test_registry_hub")
def setup_test_registry(client, monkeypatch):
    container = client.app.container
    test_registry = ComponentRegistry(initial_components=[MockDatasetSource, MockDataLoader])
    monkeypatch.setitem(container._services, "component_registry", test_registry)
    return test_registry


def test_list_sources(client: TestClient):
    response = client.get("/api/v1/dataset-source/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "MockDatasetSource"
    assert data[0]["type"] == "DatasetSource"


def test_search_returns_entries(client: TestClient):
    response = client.get("/api/v1/dataset-source/MockDatasetSource/search?q=test&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "mock/dataset"
    assert data[0]["name"] == "Mock Dataset"


def test_search_empty_result(client: TestClient):
    response = client.get("/api/v1/dataset-source/MockDatasetSource/search?q=error")
    assert response.status_code == 200
    assert response.json() == []


def test_search_unknown_source(client: TestClient):
    response = client.get("/api/v1/dataset-source/UnknownSource/search?q=test")
    assert response.status_code == 404


def test_get_download_url(client: TestClient):
    response = client.get("/api/v1/dataset-source/MockDatasetSource/mock%2Fdataset/download-url")
    assert response.status_code == 200
    assert response.json() == {"url": "https://mock.example.com/mock/dataset"}


def test_get_download_url_unknown_source(client: TestClient):
    response = client.get("/api/v1/dataset-source/Unknown/some-id/download-url")
    assert response.status_code == 404


def test_get_preview(client: TestClient):
    response = client.get(
        "/api/v1/dataset-source/MockDatasetSource/mock%2Fdataset/preview?n_rows=3"
    )
    assert response.status_code == 200
    data = response.json()
    assert "sample" in data
    assert "inferred_types" in data
    assert "preview_row_count" in data
    assert len(data["sample"]) == 3


def test_import_endpoint_creates_dataset_and_job(client: TestClient):
    """POST import creates a Dataset record and enqueues a DatasetJob."""
    create_resp = client.post("/api/v1/dataset/", json={"name": "hub_import_test"})
    assert create_resp.status_code == 201
    dataset_id = create_resp.json()["id"]

    response = client.post(
        "/api/v1/dataset-source/MockDatasetSource/mock%2Fdataset/import",
        json={
            "dataset_id": dataset_id,
            "params": {},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["dataset_id"] == dataset_id


def test_import_endpoint_unknown_source(client: TestClient):
    response = client.post(
        "/api/v1/dataset-source/Unknown/some%2Fdataset/import",
        json={"dataset_id": 999, "params": {}},
    )
    assert response.status_code == 404
