"""Exporting a run as a package, loading it outside the app, and the endpoint.

Two runs are fitted by hand (training through ModelJob is slow and not what is
under test): a classifier behind a Binarizer preprocessing step, so the fitted
preprocessor has to travel with the package, and a plain regressor.
"""

import json
import random
import zipfile
from pathlib import Path

import pyarrow as pa
import pytest
from fastapi.testclient import TestClient

from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.model_package.export import (
    RunNotExportableError,
    build_package,
)
from DashAI.back.model_package.manifest import (
    MANIFEST_ENTRY,
    PREPROCESSOR_ENTRY,
    SCHEMA_ENTRY,
)
from DashAI.back.preprocessing.session_preprocessor import load_final_preprocessor

RAW_INPUT_COLUMNS = [
    "SepalLengthCm",
    "SepalWidthCm",
    "PetalLengthCm",
    "PetalWidthCm",
]
DERIVED_COLUMN = "bin_SepalLengthCm"
CLASS_COLUMN = "Species"
REGRESSION_INPUTS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm"]
REGRESSION_TARGET = "PetalWidthCm"
IRIS_ROWS = 150
SPLITS = {
    "splitter_name": "HoldoutSplitter",
    "splitType": "random",
    "train": 0.5,
    "test": 0.2,
    "validation": 0.3,
    "is_random": True,
    "has_changed": True,
    "seed": 42,
    "shuffle": True,
    "stratify": False,
}


def _split_indexes():
    rows = list(range(IRIS_ROWS))
    random.Random(875).shuffle(rows)
    return {
        "train_indexes": sorted(rows[:75]),
        "test_indexes": sorted(rows[75:105]),
        "val_indexes": sorted(rows[105:]),
    }


def _finished_run(session_factory, session_id, model_name, parameters, path):
    with session_factory() as db:
        run = Run(
            model_session_id=session_id,
            model_name=model_name,
            parameters=parameters,
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={
                "n_trials": 1,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            name=f"Package {model_name}",
            goal_metric="Accuracy",
            run_path=str(path),
            split_indexes=json.dumps(_split_indexes()),
        )
        run.set_status_as_finished()
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id


@pytest.fixture(scope="module", name="classifier_run_id")
def fit_a_classifier_behind_preprocessing(
    client: TestClient, dataset_1: Dataset, tmp_path_factory
):
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "model-package-classifier-session",
            "input_columns": [],
            "output_columns": [CLASS_COLUMN],
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(SPLITS),
            "preprocessing": [
                {
                    "converter": "Binarizer",
                    "params": {"threshold": 3.0},
                    "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
                },
            ],
            "input_column_refs": [{"kind": "group", "step": 0}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["preprocessing_status"] == "ready", body

    registry = client.app.container["component_registry"]
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = db.get(ModelSession, body["id"])
        db.expunge(session)

    raw = load_dataset(str(Path(dataset_1.file_path) / "dataset"))
    preprocessor = load_final_preprocessor(session)
    task = registry["TabularClassificationTask"]["class"]()
    transformed = task.prepare_for_task(
        preprocessor.transform_dataset(raw), [DERIVED_COLUMN], [CLASS_COLUMN]
    )
    parameters = {"n_neighbors": 3, "weights": "uniform", "algorithm": "auto"}
    model = registry["KNeighborsClassifier"]["class"](**parameters)
    train = transformed.select(_split_indexes()["train_indexes"])
    model.train(
        train.select_columns([DERIVED_COLUMN]), train.select_columns([CLASS_COLUMN])
    )
    path = tmp_path_factory.mktemp("model-package-classifier") / "model"
    model.save(str(path))
    return _finished_run(
        session_factory, session.id, "KNeighborsClassifier", parameters, path
    )


@pytest.fixture(scope="module", name="regressor_run_id")
def fit_a_regressor(client: TestClient, dataset_1: Dataset, tmp_path_factory):
    registry = client.app.container["component_registry"]
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = ModelSession(
            dataset_id=dataset_1.id,
            name="model-package-regressor-session",
            task_name="RegressionTask",
            input_columns=REGRESSION_INPUTS,
            output_columns=[REGRESSION_TARGET],
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits=json.dumps(SPLITS),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    raw = load_dataset(str(Path(dataset_1.file_path) / "dataset"))
    task = registry["RegressionTask"]["class"]()
    prepared = task.prepare_for_task(raw, REGRESSION_INPUTS, [REGRESSION_TARGET])
    model = registry["LinearRegression"]["class"]()
    train = prepared.select(_split_indexes()["train_indexes"])
    model.train(
        train.select_columns(REGRESSION_INPUTS),
        train.select_columns([REGRESSION_TARGET]),
    )
    path = tmp_path_factory.mktemp("model-package-regressor") / "model"
    model.save(str(path))
    return _finished_run(session_factory, session_id, "LinearRegression", {}, path)


def _export(client, run_id, destination):
    return build_package(
        run_id,
        destination,
        client.app.container["session_factory"],
        client.app.container["component_registry"],
    )


def test_a_package_carries_the_model_preprocessor_and_an_empty_schema(
    client, classifier_run_id, tmp_path
):
    destination = tmp_path / "classifier.dashai-model"
    manifest = _export(client, classifier_run_id, destination)

    assert manifest["model"]["name"] == "KNeighborsClassifier"
    assert manifest["task"]["name"] == "TabularClassificationTask"
    assert manifest["input_columns"] == [DERIVED_COLUMN]
    assert manifest["output_columns"] == [CLASS_COLUMN]
    assert manifest["has_preprocessing"] is True
    assert manifest["plugins"] == []

    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert MANIFEST_ENTRY in names
        assert PREPROCESSOR_ENTRY in names
        assert json.loads(archive.read(MANIFEST_ENTRY)) == manifest
        schema_bytes = archive.read(f"{SCHEMA_ENTRY}/data.arrow")

    table = pa.ipc.open_file(pa.py_buffer(schema_bytes)).read_all()
    assert table.num_rows == 0
    types = json.loads(table.schema.metadata[b"dashai_types"])
    assert "Iris-setosa" in types[CLASS_COLUMN]["categories"]


def test_an_unfinished_run_cannot_be_exported(client, dataset_1, tmp_path):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = ModelSession(
            dataset_id=dataset_1.id,
            name="model-package-unfinished-session",
            task_name="TabularClassificationTask",
            input_columns=RAW_INPUT_COLUMNS,
            output_columns=[CLASS_COLUMN],
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits=json.dumps(SPLITS),
        )
        db.add(session)
        db.commit()
        run = Run(
            model_session_id=session.id,
            model_name="KNeighborsClassifier",
            parameters={},
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={},
            name="Unfinished",
            goal_metric="Accuracy",
        )
        db.add(run)
        db.commit()
        run_id = run.id

    with pytest.raises(RunNotExportableError):
        _export(client, run_id, tmp_path / "unfinished.dashai-model")
