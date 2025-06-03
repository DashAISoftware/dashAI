import json
import os

import joblib
import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import (
    Experiment,
    GlobalExplainer,
    LocalExplainer,
    Run,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.explainability.local_explainer import BaseLocalExplainer
from DashAI.back.job import ExplainerJob
from DashAI.back.models import BaseModel
from DashAI.back.tasks import BaseTask

input_columns = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
output_columns = ["Species"]
splits = json.dumps(
    {
        "train": 0.5,
        "test": 0.2,
        "validation": 0.3,
        "is_random": True,
        "has_changed": True,
        "seed": 42,
        "shuffle": True,
        "stratify": False,
    }
)


@pytest.fixture(scope="module", name="dataset_id")
def create_dataset(client):
    """Create testing dataset using job system."""
    abs_file_path = os.path.join(os.path.dirname(__file__), "iris.csv")

    with open(abs_file_path, "rb") as csv:
        # Preparar los parámetros en el formato que espera el job
        params = {
            "dataloader": "CSVDataLoader",
            "name": "DummyDataset6",
            "separator": ",",
        }

        kwargs = {
            "name": "DummyDataset6",
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

        assert (
            response.status_code == 201
        ), f"Failed to create dataset job: {response.text}"

        client.post("/api/v1/job/start/", params={"stop_when_queue_empties": True})

        datasets_response = client.get("/api/v1/dataset/")
        assert datasets_response.status_code == 200, datasets_response.text

        datasets = datasets_response.json()
        dataset_id = None
        for dataset in datasets:
            if dataset["name"] == "DummyDataset6":
                dataset_id = dataset["id"]
                break

        assert dataset_id is not None, "Dataset not found after job completion"

    yield dataset_id

    response = client.delete(f"/api/v1/dataset/{dataset_id}")
    assert response.status_code == 204, response.text


class DummyTask(BaseTask):
    name: str = "DummyTask"

    def prepare_for_task(self, datasetdict, outputs_columns):
        return datasetdict


class DummyModel(BaseModel):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    @classmethod
    def get_schema(cls):
        return {}

    def save(self, filename):
        joblib.dump(self, filename)

    def load(self, filename):
        return

    def predict(self, x):
        return {}

    def fit(self, x, y):
        return


class DummyGlobalExplainer(BaseGlobalExplainer):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def explain(self, dataset):
        return

    def plot(self, explanation):
        return


class DummyLocalExplainer(BaseLocalExplainer):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def fit(self, dataset):
        return

    def explain_instance(self, instances):
        return

    def plot(self, explanation):
        return


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    """Setup a test registry with test task and explainers components."""
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            DummyTask,
            DummyModel,
            DummyGlobalExplainer,
            DummyLocalExplainer,
            ExplainerJob,
        ]
    )

    monkeypatch.setitem(
        container._services,
        "component_registry",
        test_registry,
    )
    return test_registry


@pytest.fixture(scope="module", name="experiment_id", autouse=True)
def create_experiment(client: TestClient, dataset_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        experiment = Experiment(
            dataset_id=dataset_id,
            name="DummyExperiment",
            task_name="DummyTask",
            input_columns=input_columns,
            output_columns=output_columns,
            splits=splits,
            indexes="""{
                "train_indexes": [0, 1, 2, 3, 4],
                "test_indexes": [5, 6, 7, 8],
                "val_indexes": [9, 10, 11, 12]
            }""",
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        yield experiment.id

        db.delete(experiment)
        db.commit()
        db.close()


@pytest.fixture(scope="module", name="run_id")
def create_run_id(client: TestClient, experiment_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        run = Run(
            experiment_id=experiment_id,
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            model_name="DummyModel",
            parameters={},
            goal_metric="Accuracy",
            name="Run",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        yield run.id

        db.delete(run)
        db.commit()
        db.close()


# Create dummys explainers
@pytest.fixture(scope="module", name="global_explainer_id")
def create_global_explainer(client: TestClient, run_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        global_explainer = GlobalExplainer(
            name="test_global",
            run_id=run_id,
            explainer_name="DummyGlobalExplainer",
            parameters={},
        )
        db.add(global_explainer)
        db.commit()
        db.refresh(global_explainer)

        yield global_explainer.id

        db.delete(global_explainer)
        db.commit()
        db.close()


@pytest.fixture(scope="module", name="local_explainer_id")
def create_local_explainer(client: TestClient, run_id: int, dataset_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        local_explainer = LocalExplainer(
            name="test_local",
            run_id=run_id,
            explainer_name="DummyLocalExplainer",
            dataset_id=dataset_id,
            parameters={},
            fit_parameters={},
        )
        db.add(local_explainer)
        db.commit()
        db.refresh(local_explainer)

        yield local_explainer.id

        db.delete(local_explainer)
        db.commit()
        db.close()


def test_enqueue_explainer_jobs(
    client: TestClient, global_explainer_id: int, local_explainer_id: int
):
    form_data_global = {
        "job_type": "ExplainerJob",
        "kwargs": json.dumps(
            {
                "explainer_id": global_explainer_id,
                "explainer_scope": "global",
            }
        ),
    }

    response = client.post(
        "/api/v1/job/",
        data=form_data_global,
    )
    assert response.status_code == 201, response.text
    created_job = response.json()
    assert created_job["kwargs"]["job_type"] == "ExplainerJob"
    assert created_job["kwargs"]["explainer_id"] == global_explainer_id

    response = client.get(f"/api/v1/job/{created_job['id']}")
    assert response.status_code == 200, response.text
    gotten_job = response.json()
    assert gotten_job["id"] == created_job["id"]
    assert gotten_job["kwargs"] == created_job["kwargs"]
    assert gotten_job["kwargs"]["job_type"] == created_job["kwargs"]["job_type"]

    form_data_local = {
        "job_type": "ExplainerJob",
        "kwargs": json.dumps(
            {
                "explainer_id": local_explainer_id,
                "explainer_scope": "local",
            }
        ),
    }

    response = client.post(
        "/api/v1/job/",
        data=form_data_local,
    )
    assert response.status_code == 201, response.text
    created_job_2 = response.json()
    assert created_job_2["id"] != created_job["id"]

    response = client.get("/api/v1/job")
    assert response.status_code == 200, response.text
    gotten_jobs = response.json()
    assert gotten_jobs[0]["id"] == created_job["id"]
    assert gotten_jobs[1]["id"] == created_job_2["id"]


def test_execute_jobs(
    client: TestClient,
    global_explainer_id: int,
    local_explainer_id: int,
    run_id: int,
    dataset_id: int,
):
    form_data_global = {
        "job_type": "ExplainerJob",
        "kwargs": json.dumps(
            {
                "explainer_id": global_explainer_id,
                "explainer_scope": "global",
            }
        ),
    }

    response = client.post(
        "/api/v1/job/",
        data=form_data_global,
    )
    assert response.status_code == 201, response.text

    form_data_local = {
        "job_type": "ExplainerJob",
        "kwargs": json.dumps(
            {
                "explainer_id": local_explainer_id,
                "explainer_scope": "local",
            }
        ),
    }

    response = client.post(
        "/api/v1/job/",
        data=form_data_local,
    )
    assert response.status_code == 201, response.text

    response = client.get(f"/api/v1/explainer/global/?run_id={run_id}")
    data = response.json()
    for explainer in data:
        assert explainer["status"] == 1

    response = client.get(f"/api/v1/explainer/local/?run_id={run_id}")
    data = response.json()
    for explainer in data:
        assert explainer["status"] == 1

    response = client.post("/api/v1/job/start/?stop_when_queue_empties=True")
    assert response.status_code == 202, response.text

    response = client.get(f"/api/v1/explainer/global/?run_id={run_id}")
    data = response.json()
    for explainer in data:
        assert explainer["status"] == 3

    response = client.get(f"/api/v1/explainer/local/?run_id={run_id}")
    data = response.json()
    for explainer in data:
        assert explainer["status"] == 3


def test_job_with_wrong_explainer(client: TestClient):
    form_data_wrong = {
        "job_type": "ExplainerJob",
        "kwargs": json.dumps({"explainer_id": 31415, "explainer_scope": "local"}),
    }

    response = client.post(
        "/api/v1/job/",
        data=form_data_wrong,
    )
    assert response.status_code == 500, response.text
