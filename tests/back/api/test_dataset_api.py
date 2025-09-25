import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(name="response_1", autouse=True)
def create_dataset_1(client):
    """Create testing dataset 1 using job system."""
    abs_file_path = os.path.join(os.path.dirname(__file__), "iris.csv")

    with open(abs_file_path, "rb") as csv:
        params = {
            "dataloader": "CSVDataLoader",
            "name": "test_csv",
            "separator": ",",
        }

        kwargs = {
            "name": "test_csv",
            "url": "",
            "params": params,
        }

        form_data = {"job_type": "DatasetJob", "kwargs": json.dumps(kwargs)}

        files = {"file": ("iris.csv", csv, "text/csv")}
        headers = {"filename": "iris.csv"}

        response = client.post(
            "/api/v1/job/",
            data=form_data,
            files=files,
            headers=headers,
        )

    return response


@pytest.fixture(name="response_2", autouse=True)
def create_dataset_2(client):
    """Create testing dataset 2 using job system."""
    abs_file_path = os.path.join(os.path.dirname(__file__), "iris.csv")

    with open(abs_file_path, "rb") as csv:
        params = {
            "dataloader": "CSVDataLoader",
            "name": "test_csv2",
            "separator": ",",
        }

        kwargs = {
            "name": "test_csv2",
            "url": "",
            "params": params,
        }

        # Crear un formulario multipart similar a job.ts
        form_data = {"job_type": "DatasetJob", "kwargs": json.dumps(kwargs)}

        files = {"file": ("iris.csv", csv, "text/csv")}
        headers = {"filename": "iris.csv"}

        response = client.post(
            "/api/v1/job/",
            data=form_data,
            files=files,
            headers=headers,
        )

    return response


def test_create_csv_dataset(client: TestClient, response_1, response_2) -> None:
    assert response_1.status_code == 201, response_1.text
    response_1 = client.get("/api/v1/dataset/1")
    assert response_1.status_code == 200, response_1.text
    data = response_1.json()
    assert data["name"] == "test_csv"
    response_2 = client.get("/api/v1/dataset/2")
    assert response_2.status_code == 200, response_2.text
    data = response_2.json()
    assert data["name"] == "test_csv2"


def test_get_all_datasets(client: TestClient):
    response = client.get("/api/v1/dataset/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data[0]["name"] == "test_csv"
    assert data[1]["name"] == "test_csv2"


def test_get_unexistant_dataset(client: TestClient):
    response = client.get("/api/v1/dataset/31415")
    assert response.status_code == 404, response.text
    assert response.text == '{"detail":"Dataset not found"}'


def test_get_types(client: TestClient):
    response = client.get("/api/v1/dataset/2/types")
    data = response.json()
    assert data == {
        "SepalLengthCm": {"type": "Value", "dtype": "float64"},
        "SepalWidthCm": {"type": "Value", "dtype": "float64"},
        "PetalLengthCm": {"type": "Value", "dtype": "float64"},
        "PetalWidthCm": {"type": "Value", "dtype": "float64"},
        "Species": {"type": "Value", "dtype": "string"},
    }


def test_modify_dataset_name(client: TestClient):
    response = client.patch(
        "/api/v1/dataset/2",
        json={"name": "test_modify_name"},
    )
    assert response.status_code == 200, response.text
    response = client.get("/api/v1/dataset/2")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "test_modify_name"


def test_delete_dataset(client: TestClient):
    response = client.delete("/api/v1/dataset/1")
    assert response.status_code == 204, response.text

    response = client.delete("/api/v1/dataset/2")
    assert response.status_code == 204, response.text
