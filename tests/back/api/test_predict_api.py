import json
import os
from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader
from DashAI.back.dataloaders.classes.json_dataloader import JSONDataLoader
from DashAI.back.dependencies.database.models import Dataset, Experiment, Run
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.metrics import BaseMetric
from DashAI.back.models import BaseModel
from DashAI.back.optimizers import OptunaOptimizer
from DashAI.back.tasks import BaseTask


class DummyTask(BaseTask):
    name: str = "DummyTask"

    def prepare_for_task(self, dataset, output_columns):
        return dataset


class DummyModel(BaseModel):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def save(self, filename):
        joblib.dump(self, filename)

    def load(self, filename):
        return

    def predict(self, x):
        return {}

    def fit(self, x, y):
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
            DummyMetric,
            CSVDataLoader,
            JSONDataLoader,
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


@pytest.fixture(scope="module", name="dataset", autouse=True)
def create_dataset(client: TestClient):
    """Create testing dataset using job system for JSON dataset."""
    abs_file_path = Path(__file__).parent / "irisDataset.json"

    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        json_dataset_entry = Dataset(
            name="test_json",
            file_path="",
        )
        db.add(json_dataset_entry)
        db.commit()
        db.refresh(json_dataset_entry)

        kwargs = {
            "dataset_id": json_dataset_entry.id,
            "url": "",
            "params": {
                "dataloader": "JSONDataLoader",
                "name": json_dataset_entry.name,
                "data_key": "data",
            },
            "file_path": abs_file_path,
        }
        job = DatasetJob(job_type="DatasetJob", kwargs=kwargs, db=db)
        job.run()

        db.refresh(json_dataset_entry)

        dataset = {
            "id": json_dataset_entry.id,
            "name": json_dataset_entry.name,
            "file_path": json_dataset_entry.file_path,
        }

    yield dataset

    with session_factory() as db:
        dataset_to_delete = db.get(Dataset, dataset["id"])
        if dataset_to_delete:
            db.delete(dataset_to_delete)
            db.commit()


@pytest.fixture(name="dataset_2", autouse=True, scope="module")
def create_dataset_2(client: TestClient):
    """Create testing dataset 2 using CSV file."""
    abs_file_path = Path(__file__).parent / "iris.csv"

    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        csv_dataset_entry = Dataset(
            name="test_csv",
            file_path="",
        )
        db.add(csv_dataset_entry)
        db.commit()
        db.refresh(csv_dataset_entry)

        kwargs = {
            "dataset_id": csv_dataset_entry.id,
            "url": "",
            "params": {
                "dataloader": "CSVDataLoader",
                "separator": ",",
                "name": csv_dataset_entry.name,
            },
            "file_path": abs_file_path,
        }
        job = DatasetJob(job_type="DatasetJob", kwargs=kwargs, db=db)
        job.run()

        db.refresh(csv_dataset_entry)

        dataset = {
            "id": csv_dataset_entry.id,
            "name": csv_dataset_entry.name,
            "file_path": csv_dataset_entry.file_path,
        }

    yield dataset

    with session_factory() as db:
        dataset_to_delete = db.get(Dataset, dataset["id"])
        if dataset_to_delete:
            db.delete(dataset_to_delete)
            db.commit()


@pytest.fixture(scope="module", name="experiment_id", autouse=True)
def create_experiment(client: TestClient, dataset: Dataset):
    session_factory = client.app.container["session_factory"]

    with session_factory() as db:
        experiment = Experiment(
            dataset_id=dataset["id"],
            name="Experiment",
            task_name="TabularClassificationTask",
            input_columns=["feature_0", "feature_1", "feature_2", "feature_3"],
            output_columns=["class"],
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
                }
            ),
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
            model_name="KNeighborsClassifier",
            parameters={},
            name="Run",
            goal_metric="Accuracy",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        yield run.id

        db.delete(run)
        db.commit()
        db.close()


@pytest.fixture(name="trained_run_id", scope="module", autouse=True)
def create_trained_run(client: TestClient, run_id: int):
    form_data = {"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})}

    response = client.post(
        "/api/v1/job/",
        data=form_data,
    )
    assert response.status_code == 201, response.text

    job_id = response.json()["id"]
    job_status = client.get(f"/api/v1/job/status/{job_id}").json()
    assert job_status["status"] == "finished", f"Model job failed: {job_status}"

    return run_id


@pytest.fixture(scope="module", name="prediction_name", autouse=True)
def create_prediction(client: TestClient, trained_run_id: int, dataset: Dataset):
    kwargs = {
        "run_id": trained_run_id,
        "id": dataset["id"],
        "json_filename": "predictTest",
    }

    form_data = {"job_type": "PredictJob", "kwargs": json.dumps(kwargs)}

    response = client.post(
        "/api/v1/job/",
        data=form_data,
    )
    assert response.status_code == 201, response.text

    job_id = response.json()["id"]
    job_status = client.get(f"/api/v1/job/status/{job_id}").json()
    assert job_status["status"] == "finished", f"Predict job failed: {job_status}"

    return kwargs["json_filename"] + ".json"


def test_get_metadata_prediction_json(client: TestClient):
    config = client.app.container["config"]
    path = Path(f"{config['DATASETS_PATH']}/predictions/")
    response = client.get("/api/v1/predict/metadata_json/", params={"path": path})
    assert response.status_code == 200, response.text
    json_data = {
        "id": 1,
        "pred_name": "predictTest.json",
        "run_name": "KNeighborsClassifier",
        "model_name": "Run",
        "dataset_name": "test_json",
        "task_name": "TabularClassificationTask",
    }
    assert response.json() == [json_data]


def test_get_prediction_table(client: TestClient):
    response = client.get("/api/v1/predict/prediction_table")
    assert response.status_code == 200, response.text
    prediction_data = response.json()

    assert isinstance(prediction_data, list)
    table_dict = prediction_data[0]
    assert table_dict["id"] == 1
    assert table_dict["run_name"] == "KNeighborsClassifier"
    assert table_dict["model_name"] == "Run"
    assert table_dict["dataset_name"] == "test_json"
    assert table_dict["task_name"] == "TabularClassificationTask"


def test_model_table(client: TestClient):
    response = client.get("/api/v1/predict/model_table")
    assert response.status_code == 200, response.text
    model_data = response.json()
    table_dict = model_data[0]
    assert table_dict["id"] == 1
    assert table_dict["experiment_name"] == "Experiment"
    assert table_dict["run_name"] == "Run"
    assert table_dict["task_name"] == "TabularClassificationTask"
    assert table_dict["model_name"] == "KNeighborsClassifier"
    assert table_dict["dataset_name"] == "test_json"
    assert table_dict["dataset_id"] == 1


def test_predict_summary(client: TestClient, prediction_name: str):
    response = client.get(
        f"/api/v1/predict/predict_summary?pred_name={prediction_name}"
    )
    assert response.status_code == 200, response.text
    summary = response.json()

    assert summary["total_data_points"] == 150
    assert summary["Unique_classes"] == 3
    assert len(summary["class_distribution"]) == 3
    assert len(summary["sample_data"]) == 50


def test_filter_datasets_endpoint(
    client: TestClient, dataset: Dataset, dataset_2: Dataset
):
    list_datasets = [dataset["file_path"], dataset_2["file_path"]]
    params = {
        "train_dataset_id": 1,
        "datasets": list_datasets,
    }
    response = client.post("/api/v1/predict/filter_datasets", json=params)
    assert response.status_code == 200, response.text
    filtered_datasets = response.json()
    assert len(filtered_datasets) == 1
    assert (
        filtered_datasets[0]["id"] == 1
    )  # only the first dataset is used to train the model


@pytest.fixture(name="json_data")
def read_json_as_dict(client: TestClient, prediction_name: str):
    config = client.app.container["config"]
    path = Path(f"{config['DATASETS_PATH']}/predictions/{prediction_name}")
    with open(path, mode="r", encoding="utf-8") as json_file:
        data = json.load(json_file)  # Carga el JSON como diccionario o lista
    return data["prediction"]


def test_download_prediction(client: TestClient, json_data: list, prediction_name: str):
    response = client.get(f"/api/v1/predict/download/{prediction_name}")
    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == json_data


def test_rename_prediction(client: TestClient, prediction_name: str):
    new_name = "renamed_prediction"
    response = client.patch(
        f"/api/v1/predict/{prediction_name}",
        json={"predict_name": prediction_name, "new_name": new_name},
    )
    assert response.status_code == 200, response.text
    data_path = client.app.container["config"]["DATASETS_PATH"]
    assert os.path.exists(Path(f"{data_path}/predictions/{new_name}.json"))
    old_name = f"{prediction_name}"[:-5]  # remove .json extension
    client.patch(
        f"/api/v1/predict/{new_name}.json",
        json={"predict_name": new_name + ".json", "new_name": old_name},
    )


def test_delete_prediction(client: TestClient, prediction_name: str):
    response = client.delete(f"/api/v1/predict/{prediction_name}")
    assert response.status_code == 200, response.text
    data_path = client.app.container["config"]["DATASETS_PATH"]
    assert not os.path.exists(Path(f"{data_path}/predictions/{prediction_name}"))
