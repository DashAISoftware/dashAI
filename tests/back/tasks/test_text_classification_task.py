import json
import os

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset, Experiment, Run


@pytest.fixture(scope="module", name="dataset", autouse=True)
def create_dataset(client: TestClient):
    """Create testing dataset using job system."""
    script_dir = os.path.dirname(__file__)
    test_dataset = "ImdbSentimentDatasetSmall.json"
    abs_file_path = os.path.join(script_dir, test_dataset)

    with open(abs_file_path, "rb") as json_file:
        params = {
            "dataloader": "JSONDataLoader",
            "name": "test_json",
            "data_key": "data",
        }

        kwargs = {
            "name": "test_json",
            "url": "",
            "params": params,
        }

        form_data = {"job_type": "DatasetJob", "kwargs": json.dumps(kwargs)}

        files = {
            "file": ("ImdbSentimentDatasetSmall.json", json_file, "application/json")
        }
        headers = {
            "filename": "ImdbSentimentDatasetSmall.json",
        }

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
        dataset = None
        for d in datasets:
            if d["name"] == "test_json":
                dataset = d
                break

        assert dataset is not None, "Dataset not found after job completion"

    yield dataset

    response = client.delete(f"/api/v1/dataset/{dataset['id']}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="module", name="experiment_id", autouse=True)
def create_experiment(client: TestClient, dataset: Dataset):
    session_factory = client.app.container["session_factory"]

    with session_factory() as db:
        experiment = Experiment(
            dataset_id=dataset["id"],
            name="Experiment",
            task_name="TextClassificationTask",
            input_columns=["text"],
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
                    "stratify": True,
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
                "metric": "auto",
            },
            model_name="DistilBertTransformer",
            parameters={
                "num_train_epochs": 5,
                "batch_size": 8,
                "learning_rate": 5e-5,
                "device": "gpu",
                "weight_decay": 0.0,
            },
            name="Run",
            goal_metric="accuracy",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        yield run.id

        db.delete(run)
        db.commit()
        db.close()


def test_create_trained_run(client: TestClient, run_id: int):
    form_data = {"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})}

    response = client.post(
        "/api/v1/job/",
        data=form_data,
    )
    assert response.status_code == 201, response.text

    response = client.post("/api/v1/job/start/?stop_when_queue_empties=True")
    assert response.status_code == 202, response.text

    response = client.get(f"/api/v1/run/{run_id}")
    assert response.status_code == 200, response.text

    return run_id
