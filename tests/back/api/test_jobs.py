import json
import os

import joblib
import pytest
from datasets import ClassLabel, Value
from fastapi.testclient import TestClient

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.model_job import ModelJob
from DashAI.back.metrics import BaseMetric
from DashAI.back.models import BaseModel
from DashAI.back.optimizers import OptunaOptimizer
from DashAI.back.tasks import BaseTask


class DummyTask(BaseTask):
    name: str = "DummyTask"
    metadata: dict = {
        "inputs_types": [ClassLabel, Value],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def prepare_for_task(self, dataset, input_columns=None, output_columns=None):
        return dataset

    def num_labels(self, dataset, output_column):
        return None


class DummyModel(BaseModel):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def save(self, filename):
        joblib.dump(self, filename)

    def load(self, filename):
        return

    def predict(self, x):
        return {}

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return

    def prepare_dataset(self, dataset, is_fit=False):
        return


class FailDummyModel(BaseModel):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def save(self, filename):
        return

    def load(self, filename):
        return

    def predict(self, x):
        return {}

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        raise Exception("Always fails")

    def prepare_dataset(self, dataset, is_fit=False):
        return


class DummyMetric(BaseMetric):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    @staticmethod
    def score(true_labels: list, probs_pred_labels: list):
        return 1


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    """Setup a test registry with test task, dataloader and model components."""
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            DummyTask,
            DummyModel,
            FailDummyModel,
            DummyMetric,
            CSVDataLoader,
            ModelJob,
            OptunaOptimizer,
        ]
    )

    monkeypatch.setitem(
        container._services,
        "component_registry",
        test_registry,
    )
    return test_registry


@pytest.fixture(scope="module", name="dataset_id")
def dataset_id(dataset_1: Dataset) -> int:
    """Get the dataset ID from the dataset_1 fixture."""
    return dataset_1.id


@pytest.fixture(scope="module", name="model_session_id", autouse=True)
def create_model_session(client: TestClient, dataset_id: int):
    container = client.app.container
    session = container["session_factory"]

    with session() as db:
        model_session = ModelSession(
            dataset_id=dataset_id,
            name="DummyExperiment",
            task_name="DummyTask",
            input_columns=["SepalLengthCm"],
            output_columns=["Species"],
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            splits=json.dumps(
                {
                    "train": 0.5,
                    "test": 0.2,
                    "validation": 0.3,
                    "is_random": True,
                    "has_changed": True,
                    "seed": 42,
                    "shuffle": True,
                    "stratify": False,
                    "splitType": "random",
                }
            ),
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)

        yield model_session.id

        db.delete(model_session)
        db.commit()
        db.close()


@pytest.fixture(scope="module", name="run_id", autouse=True)
def create_run(client: TestClient, model_session_id: int):
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": model_session_id,
            "model_name": "DummyModel",
            "name": "DummyRun",
            "parameters": {},
            "optimizer_name": "",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "",
            "description": "This is a test run",
            "plot_history_path": "path/to/history.png",
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert response.status_code == 201, response.text
    run = response.json()

    yield run["id"]

    response = client.delete(f"/api/v1/run/{run['id']}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="module", name="failed_run_id", autouse=True)
def create_failed_run(client: TestClient, model_session_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        run = Run(
            model_session_id=model_session_id,
            model_name="FailDummyModel",
            parameters={},
            optimizer_name="",
            optimizer_parameters={
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            goal_metric="",
            name="DummyRun2",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        yield run.id

        db.delete(run)
        db.commit()
        db.close()


def test_enqueue_jobs(client: TestClient, run_id: int):
    form_data = {"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})}

    response = client.post("/api/v1/job/", data=form_data)
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]

    response = client.get(f"/api/v1/job/status/{job_id}")
    assert response.status_code == 200, response.text
    job_status = response.json()

    assert job_status["status"] in [
        "finished",
        "error",
    ], f"Job status should be finished or error, got {job_status['status']}"
    if job_status["status"] == "error":
        assert "error" in job_status, "Error jobs should have an error message"

    response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})},
    )
    assert response.status_code == 201, response.text
    job_id_2 = response.json()["id"]
    assert job_id_2 != job_id, "Job IDs should be different"

    response = client.get(f"/api/v1/job/status/{job_id_2}")
    assert response.status_code == 200, response.text
    job_status_2 = response.json()
    assert job_status_2["status"] in ["finished", "error"]

    response = client.get("/api/v1/job")
    assert response.status_code == 200, response.text
    job_list = response.json()
    job_ids = [job["id"] for job in job_list]
    assert job_id in job_ids, f"Job ID {job_id} not found in job list"
    assert job_id_2 in job_ids, f"Job ID {job_id_2} not found in job list"


def test_execute_jobs(client: TestClient, run_id: int, failed_run_id: int):
    response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})},
    )
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]

    response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": failed_run_id})},
    )
    assert response.status_code == 201, response.text
    failed_job_id = response.json()["id"]

    response = client.get("/api/v1/run")
    data = response.json()
    for run in data:
        assert run["status"] in [1, 3, 4]
        assert run["delivery_time"] is not None

    response = client.get(f"/api/v1/job/status/{job_id}")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "finished"

    response = client.get(f"/api/v1/job/status/{failed_job_id}")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "error"

    response = client.get(f"/api/v1/run/{run_id}")
    data = response.json()
    assert data["status"] == 3
    assert data["run_path"] is not None
    assert os.path.exists(data["run_path"])
    assert data["status"] == 3
    assert data["delivery_time"] is not None
    assert data["start_time"] is not None
    assert data["end_time"] is not None

    response = client.get(f"/api/v1/run/{failed_run_id}")
    data = response.json()
    assert data["status"] == 4
    assert data["delivery_time"] is not None
    assert data["start_time"] is not None
    assert data["end_time"] is None


def test_job_with_wrong_run(client: TestClient):
    response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": 31415})},
    )
    assert response.status_code == 500, response.text
    assert response.status_code == 500, response.text
