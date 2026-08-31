import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset


@pytest.fixture(scope="module", name="dataset_id")
def dataset_id(dataset_1: Dataset) -> int:
    """Get the dataset ID from the dataset_1 fixture."""
    return dataset_1.id


@pytest.fixture(scope="module", name="model_session_id")
def create_model_session(client: TestClient, dataset_id):
    """Create model session 1."""
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": "Test Experiment",
            "input_columns": [
                "SepalLengthCm",
                "SepalWidthCm",
                "PetalLengthCm",
                "PetalWidthCm",
            ],
            "output_columns": ["Species"],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "holdout",
            "splits": json.dumps(
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
        },
    )

    yield response.json()["id"]
    response = client.delete(f"/api/v1/model-session/{response.json()['id']}")
    assert response.status_code == 204, response.text


def test_create_run(client: TestClient, model_session_id: int):
    # create run using the model session
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": model_session_id,
            "model_name": "KNeighborsClassifier",
            "name": "Run1",
            "parameters": {"n_neighbors": 5, "weights": "uniform", "algorithm": "auto"},
            "optimizer_name": "OptunaOptimizer",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "Accuracy",
            "description": "This is a test run",
            "plot_history_path": "path/to/history.png",  # Add missing fields
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert response.status_code == 201
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": model_session_id,
            "model_name": "KNeighborsClassifier",
            "name": "Run2",
            "parameters": {
                "n_neighbors": 3,
                "weights": "uniform",
                "algorithm": "kd_tree",
            },
            "optimizer_name": "OptunaOptimizer",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "Accuracy",
            "description": "This is a test run",
            "plot_history_path": "path/to/history.png",  # Add missing fields
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert response.status_code == 201
    response = client.get("/api/v1/run/1")
    assert response.status_code == 200
    data = response.json()
    assert data["model_session_id"] == model_session_id
    assert data["model_name"] == "KNeighborsClassifier"
    assert data["name"] == "Run1"
    assert data["status"] == 0
    assert data["parameters"] == {
        "n_neighbors": 5,
        "weights": "uniform",
        "algorithm": "auto",
    }

    response = client.get("/api/v1/run/2")
    assert response.status_code == 200
    data = response.json()
    assert data["model_session_id"] == model_session_id
    assert data["model_name"] == "KNeighborsClassifier"
    assert data["name"] == "Run2"
    assert data["status"] == 0
    assert data["parameters"] == {
        "n_neighbors": 3,
        "weights": "uniform",
        "algorithm": "kd_tree",
    }


def test_create_run_with_cross_validation_strategy(client: TestClient, dataset_id: int):
    """A model session using CV should persist the CV split configuration."""
    create_session_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": "CV Session",
            "input_columns": [
                "SepalLengthCm",
                "SepalWidthCm",
                "PetalLengthCm",
                "PetalWidthCm",
            ],
            "output_columns": ["Species"],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "CrossValidationEvaluationStrategy",
            "splits": json.dumps(
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
                    "splitter_name": "KFoldSplitter",
                    "n_splits": 3,
                }
            ),
        },
    )
    assert create_session_response.status_code == 201, create_session_response.text

    session = create_session_response.json()
    response = client.get(f"/api/v1/model-session/{session['id']}")
    assert response.status_code == 200, response.text
    persisted_session = response.json()
    assert (
        persisted_session["evaluation_strategy"] == "CrossValidationEvaluationStrategy"
    )
    persisted_splits = json.loads(persisted_session["splits"])
    assert persisted_splits["splitter_name"] == "KFoldSplitter"
    assert persisted_splits["n_splits"] == 3

    create_run_response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session["id"],
            "model_name": "KNeighborsClassifier",
            "name": "CV Run",
            "parameters": {"n_neighbors": 5, "weights": "uniform", "algorithm": "auto"},
            "optimizer_name": "OptunaOptimizer",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "Accuracy",
            "description": "Cross-validation test run",
            "plot_history_path": "path/to/history.png",
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert create_run_response.status_code == 201, create_run_response.text
    created_run = create_run_response.json()
    assert created_run["name"] == "CV Run"
    assert created_run["model_session_id"] == session["id"]

    delete_session_response = client.delete(f"/api/v1/model-session/{session['id']}")
    assert delete_session_response.status_code == 204, delete_session_response.text


def test_create_model_session_persists_converters(client: TestClient, dataset_id: int):
    """`converters` set on a session must round-trip through create/get."""
    converters = [
        {
            "converter": "StandardScaler",
            "params": {"with_mean": True},
            "columns": ["SepalLengthCm"],
        }
    ]
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": "Converter Persistence Session",
            "input_columns": [
                "SepalLengthCm",
                "SepalWidthCm",
                "PetalLengthCm",
                "PetalWidthCm",
            ],
            "output_columns": ["Species"],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(
                {
                    "train": 0.6,
                    "test": 0.2,
                    "validation": 0.2,
                    "is_random": True,
                    "has_changed": True,
                    "seed": 42,
                    "shuffle": True,
                    "stratify": False,
                    "splitType": "random",
                    "splitter_name": "HoldoutSplitter",
                }
            ),
            "converters": converters,
        },
    )
    assert response.status_code == 201, response.text
    session = response.json()
    assert session["converters"] == [{**converters[0], "target_column": None}]

    get_response = client.get(f"/api/v1/model-session/{session['id']}")
    assert get_response.status_code == 200, get_response.text
    persisted = get_response.json()
    assert persisted["converters"] == [{**converters[0], "target_column": None}]
    # Creating a session with converters auto-enqueues preprocessing; in test
    # mode the job queue runs it synchronously, so it's already done by now.
    assert persisted["preprocessing_status"] == 3  # FINISHED
    assert persisted["preprocessed_path"] is not None

    delete_response = client.delete(f"/api/v1/model-session/{session['id']}")
    assert delete_response.status_code == 204, delete_response.text


def _create_and_run_session_with_converter(
    client: TestClient,
    dataset_id: int,
    evaluation_strategy: str,
    splits: dict,
    name: str,
):
    """Shared helper: create a session with a fit-dependent converter
    (StandardScaler), run it, and return (session, run_id, job_status)."""
    create_session_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": name,
            "input_columns": [
                "SepalLengthCm",
                "SepalWidthCm",
                "PetalLengthCm",
                "PetalWidthCm",
            ],
            "output_columns": ["Species"],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": evaluation_strategy,
            "splits": json.dumps(splits),
            "converters": [
                {"converter": "StandardScaler", "params": {}, "columns": []}
            ],
        },
    )
    assert create_session_response.status_code == 201, create_session_response.text
    session = create_session_response.json()

    create_run_response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session["id"],
            "model_name": "KNeighborsClassifier",
            "name": f"{name} Run",
            "parameters": {
                "n_neighbors": 5,
                "weights": "uniform",
                "algorithm": "auto",
            },
            "optimizer_name": "",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "",
            "description": f"{name} run",
            "plot_history_path": "path/to/history.png",
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert create_run_response.status_code == 201, create_run_response.text
    run_id = create_run_response.json()["id"]

    job_response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})},
    )
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]

    status_response = client.get(f"/api/v1/job/status/{job_id}")
    assert status_response.status_code == 200, status_response.text

    return session, run_id, status_response.json()


def test_run_with_session_converter_holdout_finishes(
    client: TestClient, dataset_id: int
):
    """A holdout session with a fit-dependent converter should train and
    finish, confirming the fit-on-train mechanism is wired into ModelJob."""
    session, run_id, job_status = _create_and_run_session_with_converter(
        client,
        dataset_id,
        evaluation_strategy="HoldoutEvaluationStrategy",
        splits={
            "train": 0.6,
            "test": 0.2,
            "validation": 0.2,
            "is_random": True,
            "has_changed": True,
            "seed": 42,
            "shuffle": True,
            "stratify": False,
            "splitType": "random",
            "splitter_name": "HoldoutSplitter",
        },
        name="Converter Holdout Session",
    )
    assert job_status["status"] == "finished", job_status

    run_response = client.get(f"/api/v1/run/{run_id}")
    assert run_response.status_code == 200, run_response.text
    assert run_response.json()["status"] == 3

    # Predicting on brand-new (raw, unscaled) input must still work: the
    # StandardScaler fitted at training time is replayed on this input
    # before it reaches the model (see execution.transform_for_prediction).
    predict_response = client.post(
        "/api/v1/predict/preview",
        data={
            "run_id": str(run_id),
            "manual_input_data": json.dumps(
                [
                    {
                        "SepalLengthCm": 5.1,
                        "SepalWidthCm": 3.5,
                        "PetalLengthCm": 1.4,
                        "PetalWidthCm": 0.2,
                    }
                ]
            ),
        },
    )
    assert predict_response.status_code == 200, predict_response.text
    preview = predict_response.json()
    assert preview["columns"][-1] == "Species"
    assert len(preview["rows"]) == 1
    assert preview["rows"][0][:4] == [5.1, 3.5, 1.4, 0.2]  # preview shows raw input

    client.delete(f"/api/v1/model-session/{session['id']}")


def test_run_with_session_converter_cross_validation_finishes(
    client: TestClient, dataset_id: int
):
    """A cross-validation session with a fit-dependent converter should
    train and finish: each fold (and the final full_dataset fold) fits its
    own converter independently, with no error along the way."""
    session, run_id, job_status = _create_and_run_session_with_converter(
        client,
        dataset_id,
        evaluation_strategy="CrossValidationEvaluationStrategy",
        splits={
            "train": 0.5,
            "test": 0.2,
            "validation": 0.3,
            "is_random": True,
            "has_changed": True,
            "seed": 42,
            "shuffle": False,
            "stratify": False,
            "splitType": "random",
            "splitter_name": "KFoldSplitter",
            "n_splits": 3,
        },
        name="Converter CV Session",
    )
    assert job_status["status"] == "finished", job_status

    run_response = client.get(f"/api/v1/run/{run_id}")
    assert run_response.status_code == 200, run_response.text
    assert run_response.json()["status"] == 3

    client.delete(f"/api/v1/model-session/{session['id']}")


def test_run_with_input_column_added_by_converter_finishes(
    client: TestClient, dataset_id: int
):
    """Regression test: a converter that *adds* a new column (LabelEncoder
    appending `le_<col>` next to the untouched original) used to break
    training whenever the session's final input/output selection included
    that new column — the raw dataset never had it, so `ModelJob`'s
    raw-dataset split-for-indices step (`dataset_split_utils.py`) and its
    `n_labels` computation both blew up with a `KeyError`. Both must now
    fall back to the preprocessed data instead of the raw one.

    Uses `le_Species` as an *input* (a numeric feature derived from the
    categorical target) with `Species` itself untouched as the real
    output — mirrors the actual scenario a live session hit. (Selecting a
    LabelEncoder-produced integer column as the *output* of a
    classification task is a separate, legitimate type-system rejection —
    classification targets must stay `Categorical` — not covered here.)"""
    create_session_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": "LabelEncoder Input Session",
            # `le_Species` doesn't exist on the raw dataset — LabelEncoder
            # creates it during preprocessing. One original input column is
            # dropped to keep the total column count within the raw
            # dataset's own count (`create_model_session` only checks the
            # *count*, not that every name resolves — the actual
            # name-resolution bug this test targets only surfaces later,
            # inside the job).
            "input_columns": [
                "SepalLengthCm",
                "SepalWidthCm",
                "PetalLengthCm",
                "le_Species",
            ],
            "output_columns": ["Species"],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(
                {
                    "train": 0.6,
                    "test": 0.2,
                    "validation": 0.2,
                    "is_random": True,
                    "has_changed": True,
                    "seed": 42,
                    "shuffle": True,
                    "stratify": False,
                    "splitType": "random",
                    "splitter_name": "HoldoutSplitter",
                }
            ),
            "converters": [
                {"converter": "LabelEncoder", "params": {}, "columns": ["Species"]}
            ],
        },
    )
    assert create_session_response.status_code == 201, create_session_response.text
    session = create_session_response.json()
    # Creating the session already exercises SessionPreprocessingJob's own
    # raw-dataset split call with `input_columns` including `le_Species`
    # from the start — this alone used to raise before ever reaching
    # ModelJob.
    assert session["preprocessing_status"] == 3, session  # FINISHED

    create_run_response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session["id"],
            "model_name": "KNeighborsClassifier",
            "name": "LabelEncoder Input Run",
            "parameters": {
                "n_neighbors": 5,
                "weights": "uniform",
                "algorithm": "auto",
            },
            "optimizer_name": "",
            "optimizer_parameters": {
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "",
            "description": "LabelEncoder input run",
            "plot_history_path": "path/to/history.png",
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert create_run_response.status_code == 201, create_run_response.text
    run_id = create_run_response.json()["id"]

    job_response = client.post(
        "/api/v1/job/",
        data={"job_type": "ModelJob", "kwargs": json.dumps({"run_id": run_id})},
    )
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]

    status_response = client.get(f"/api/v1/job/status/{job_id}")
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "finished", status_response.json()

    run_response = client.get(f"/api/v1/run/{run_id}")
    assert run_response.status_code == 200, run_response.text
    assert run_response.json()["status"] == 3

    client.delete(f"/api/v1/model-session/{session['id']}")


def test_get_run(client: TestClient):
    response = client.get("/api/v1/run/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Run1"
    response = client.get("/api/v1/run/2")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Run2"


def test_get_all_runs(client: TestClient, model_session_id: int):
    response = client.get(f"/api/v1/run/?model_session_id={model_session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["model_session_id"] == model_session_id
    assert data[1]["model_session_id"] == model_session_id


def test_get_wrong_run(client: TestClient):
    # Try to retrieve a non-existent run an get an error
    response = client.get("/api/v1/run/31415")
    assert response.status_code == 404
    assert response.text == '{"detail":"Run not found"}'


def test_get_wrong_runs(client: TestClient):
    response = client.get("/api/v1/run/?model_session_id=31415")
    assert response.status_code == 404


def test_modify_run(client: TestClient):
    response = client.patch(
        "/api/v1/run/1",
        json={
            "parameters": {
                "n_neighbors": 3,
                "weights": "uniform",
                "algorithm": "kd_tree",
            },
            "run_name": "RunA",
        },
    )
    assert response.status_code == 200

    response = client.get("/api/v1/run/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "RunA"
    assert data["status"] == 0
    assert data["parameters"] == {
        "n_neighbors": 3,
        "weights": "uniform",
        "algorithm": "kd_tree",
    }
    assert data["created"] != data["last_modified"]


def test_modify_run_model(client: TestClient):
    # Send an empty request body (no valid parameters)
    # This should return 304 since no parameters are being updated
    response = client.patch(
        "/api/v1/run/2",
        json={},
    )
    assert response.status_code == 304


@pytest.mark.order(-1)
def test_delete_run(client: TestClient):
    # Delete all the runs in the db
    response = client.delete("/api/v1/run/1")
    assert response.status_code == 204
    response = client.delete("/api/v1/run/2")
    assert response.status_code == 204
