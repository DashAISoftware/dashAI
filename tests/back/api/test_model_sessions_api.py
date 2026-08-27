import json

from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset, ModelSession

INPUT_COLUMNS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
OUTPUT_COLUMNS = ["Species"]

HOLDOUT_SPLITS = {
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


def test_model_session_can_be_created_without_columns(
    client: TestClient, dataset_1: Dataset
) -> None:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_1.id,
            name="No Columns Yet",
            task_name="TabularClassificationTask",
            input_columns=None,
            output_columns=None,
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits="{}",
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)
        assert model_session.input_columns is None
        assert model_session.output_columns is None
        db.delete(model_session)
        db.commit()


def test_create_session_without_columns(client: TestClient, dataset_1: Dataset) -> None:
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Step 1 Only",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": "{}",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["input_columns"] == []
    assert body["output_columns"] == []


def test_put_converters_enqueues_apply_job(
    client: TestClient, dataset_1: Dataset
) -> None:
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Converters PUT Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT_SPLITS),
        },
    )
    model_session_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/model-session/{model_session_id}/converters",
        json={
            "converters": [
                {
                    "converter": "StandardScaler",
                    "params": {},
                    "columns": INPUT_COLUMNS,
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["converters"] == [
        {
            "converter": "StandardScaler",
            "params": {},
            "columns": INPUT_COLUMNS,
            "target_column": None,
        }
    ]


def test_patch_sets_input_output_columns(
    client: TestClient, dataset_1: Dataset
) -> None:
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Patch Columns Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": "{}",
        },
    )
    model_session_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/model-session/{model_session_id}",
        params={
            "input_columns": json.dumps(["a", "b"]),
            "output_columns": json.dumps(["c"]),
        },
    )
    assert response.status_code == 200
    assert response.json()["input_columns"] == ["a", "b"]
    assert response.json()["output_columns"] == ["c"]


def test_patch_splits_invalidates_existing_converters(
    client: TestClient, dataset_1: Dataset
) -> None:
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Invalidation Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT_SPLITS),
        },
    )
    model_session_id = create_response.json()["id"]

    client.put(
        f"/api/v1/model-session/{model_session_id}/converters",
        json={
            "converters": [{"converter": "StandardScaler", "params": {}, "columns": []}]
        },
    )

    changed_splits = dict(HOLDOUT_SPLITS, train=0.5, test=0.3, validation=0.2, seed=7)
    response = client.patch(
        f"/api/v1/model-session/{model_session_id}",
        params={"splits": json.dumps(changed_splits)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["converters_invalidated"] is True
    assert body["converters"] == []
    assert body["preprocessed_path"] is None


def test_get_preprocessed_columns_reflects_applied_converters(
    client: TestClient, dataset_1: Dataset
) -> None:
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Preprocessed Columns Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT_SPLITS),
        },
    )
    model_session_id = create_response.json()["id"]

    # Before any converter: reflects the raw dataset's columns.
    response = client.get(
        f"/api/v1/model-session/{model_session_id}/preprocessed-columns"
    )
    assert response.status_code == 200
    assert set(response.json()["columns"].keys()) == set(INPUT_COLUMNS + OUTPUT_COLUMNS)

    client.put(
        f"/api/v1/model-session/{model_session_id}/converters",
        json={
            "converters": [
                {
                    "converter": "PCA",
                    "params": {"n_components": 2},
                    # No output column chosen yet, so "all columns" would
                    # include the (still categorical) target — scope
                    # explicitly to the numeric input columns instead, same
                    # as a real user would in the wizard's column picker.
                    "columns": INPUT_COLUMNS,
                }
            ]
        },
    )

    # After PCA: reflects the transformed columns.
    response = client.get(
        f"/api/v1/model-session/{model_session_id}/preprocessed-columns"
    )
    assert response.status_code == 200
    columns = response.json()["columns"]
    assert "Species" in columns
    assert len(columns) == 3  # 2 PCA components + Species


def test_validate_columns_against_preprocessed_state(
    client: TestClient, dataset_1: Dataset
) -> None:
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "Validate Against Preprocessed Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT_SPLITS),
        },
    )
    model_session_id = create_response.json()["id"]

    client.put(
        f"/api/v1/model-session/{model_session_id}/converters",
        json={
            "converters": [
                {
                    "converter": "PCA",
                    "params": {"n_components": 2},
                    "columns": INPUT_COLUMNS,
                }
            ]
        },
    )

    # A PCA component name doesn't exist in the raw dataset — validating
    # against it without model_session_id would 400/error; with it, the
    # preprocessed columns (2 PCA components + Species) are used instead.
    response = client.post(
        "/api/v1/model-session/validation",
        json={
            "task_name": "TabularClassificationTask",
            "dataset_id": dataset_1.id,
            "model_session_id": model_session_id,
            "inputs_columns": ["pca0", "pca1"],
            "outputs_columns": ["Species"],
        },
    )
    assert response.status_code == 200
    assert response.json()["dataset_status"] == "valid"


def test_put_converters_works_before_output_columns_are_chosen(
    client: TestClient, dataset_1: Dataset
) -> None:
    """The real wizard scenario Task 4's own test doesn't cover: applying a
    converter when output_columns is still empty (Preprocessing, step 2,
    comes before Columns, step 3)."""
    create_response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "No Columns PUT Converters Test",
            "input_columns": [],
            "output_columns": [],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT_SPLITS),
        },
    )
    model_session_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/model-session/{model_session_id}/converters",
        json={
            "converters": [
                {
                    "converter": "StandardScaler",
                    "params": {},
                    "columns": INPUT_COLUMNS,
                }
            ]
        },
    )
    assert response.status_code == 200

    session_response = client.get(f"/api/v1/model-session/{model_session_id}")
    body = session_response.json()
    assert body["preprocessing_status"] == 3  # FINISHED
    assert body["preprocessed_path"] is not None
