"""Regression net for replacing the session's column fields with column roles.

Written before the refactor and recorded against the code it replaces, so the
refactor has something exact to be measured against. Every scenario goes
through the API and the jobs the way the app does, and pins what a user or the
database can see: the columns stored on the session, the run's partitions and
metric rows, the saved prediction file, the manual prediction preview, a
global explanation and an exported package. Text, image and translation, which
no other test takes through a session, are pinned through a model that records
the columns and values it is handed.

**Two helpers know how a session spells its columns**: ``_create_session``
(the payload) and ``_stored_columns`` (what is read back from the row). They
are the only part of this file the refactor may change. The values live in
``column_roles_net_golden.json``, recorded once on the base with
``DASHAI_RECORD_COLUMN_ROLES_NET=1`` and never re-recorded while the refactor
is under way: a diff on that file is a behaviour change.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures from this package's ``conftest.py``.
"""

import hashlib
import json
import os
import pickle
import zipfile
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import PredictionStatus, RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import (
    Dataset,
    GlobalExplainer,
    Metric,
    ModelSession,
    Prediction,
    Run,
)
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.predict_job import PredictJob
from DashAI.back.model_package.export import build_package
from DashAI.back.model_package.load import load_model
from DashAI.back.models.base_model import BaseModel

GOLDEN_PATH = Path(__file__).with_name("column_roles_net_golden.json")
RECORDING = os.environ.get("DASHAI_RECORD_COLUMN_ROLES_NET") == "1"

IRIS_FEATURES = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
IRIS_CSV = Path(__file__).parent / "iris.csv"

# Shuffled with a fixed seed: iris is sorted by species, so unshuffled blocks
# would leave a single class in the test partition and pin almost nothing.
HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "splitType": "random",
    "train": 0.6,
    "test": 0.2,
    "validation": 0.2,
    "shuffle": True,
    "stratify": False,
    "seed": 42,
}
KFOLD = {
    "splitter_name": "KFoldSplitter",
    "n_splits": 3,
    "test_size": 0.2,
    "shuffle": True,
    "random_state": 7,
}
BINARIZER = {
    "converter": "Binarizer",
    "params": {"threshold": 3.0},
    "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
}
ONE_HOT = {
    "converter": "OneHotEncoder",
    "params": {"handle_unknown": "ignore", "dtype": "int64"},
    "scope": [{"kind": "raw", "name": "Species"}],
}
KNN = {"n_neighbors": 5, "weights": "uniform", "algorithm": "auto"}
CLASSIFICATION_METRICS = ["Accuracy", "F1"]
REGRESSION_METRICS = ["MAE", "RMSE", "R2"]

# --------------------------------------------------------------------------- #
# The two helpers that know how a session spells its columns
# --------------------------------------------------------------------------- #


def _create_session(
    client: TestClient,
    *,
    dataset_id: int,
    task: str,
    name: str,
    inputs: list,
    outputs: list,
    refs: list = None,
    preprocessing: list = (),
    strategy: str = "HoldoutEvaluationStrategy",
    splits: dict = None,
    metrics: list = (),
) -> int:
    """Create a session through the API, the way the wizard does.

    ``inputs`` are raw column names and ``refs`` the model inputs as column
    refs, which a session with preprocessing needs because some inputs are
    converter outputs.
    """
    body = {
        "dataset_id": dataset_id,
        "task_name": task,
        "name": name,
        "input_columns": [] if preprocessing else list(inputs),
        "output_columns": list(outputs),
        "train_metrics": list(metrics),
        "validation_metrics": list(metrics),
        "test_metrics": list(metrics),
        "evaluation_strategy": strategy,
        "splits": json.dumps(splits if splits is not None else HOLDOUT),
        "preprocessing": list(preprocessing),
    }
    if refs is not None:
        body["input_column_refs"] = refs
    response = client.post("/api/v1/model-session/", json=body)
    assert response.status_code == 201, response.text
    assert response.json()["preprocessing_status"] in (None, "ready"), response.text
    return response.json()["id"]


def _stored_columns(session: ModelSession) -> dict:
    """The session's columns as stored: model inputs, outputs and input refs."""
    return {
        "inputs": list(session.input_columns),
        "outputs": list(session.output_columns),
        "input_refs": [
            {k: v for k, v in ref.items() if v is not None}
            for ref in (session.input_column_refs or [])
        ],
    }


# --------------------------------------------------------------------------- #
# The golden values
# --------------------------------------------------------------------------- #

_recorded: dict = {}


@pytest.fixture(scope="module", name="golden", autouse=True)
def fixture_golden():
    if RECORDING:
        yield None
        existing = (
            json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
            if GOLDEN_PATH.exists()
            else {}
        )
        existing.update(_recorded)
        GOLDEN_PATH.write_text(
            json.dumps(existing, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        yield json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _plain(value):
    """A JSON-comparable copy: numpy scalars and arrays, tuples and frames."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, pd.DataFrame):
        return _plain(value.to_dict(orient="list"))
    if isinstance(value, pd.Series):
        return _plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, bytes):
        return hashlib.sha1(value).hexdigest()
    return value


def _pin(golden, key: str, value) -> None:
    value = json.loads(json.dumps(_plain(value)))
    if RECORDING:
        _recorded[key] = value
        return
    assert key in golden, f"{key} was never recorded"
    assert value == golden[key], key


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #


def _get(client: TestClient, model, row_id):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        row = db.get(model, row_id)
        db.expunge(row)
        return row


def _create_dataset(client: TestClient, path: Path, name: str, params: dict) -> int:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        entry = Dataset(name=name, file_path="")
        db.add(entry)
        db.commit()
        db.refresh(entry)
        DatasetJob(
            job_type="DatasetJob",
            kwargs={
                "dataset_id": entry.id,
                "url": "",
                "params": {"name": name, **params},
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _train(client: TestClient, session_id: int, model: str, params: dict) -> int:
    """Create a run without a search, the way the front does, and train it."""
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session_id,
            "model_name": model,
            "name": f"{model} run of session {session_id}",
            "parameters": params,
            "optimizer_name": "",
            "optimizer_parameters": {},
            "plot_history_path": "",
            "plot_slice_path": "",
            "plot_contour_path": "",
            "plot_importance_path": "",
            "goal_metric": "",
            "description": "",
            "nested": None,
        },
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    ModelJob(run_id=run_id).run()
    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    return run_id


def _metrics(client: TestClient, run_id: int) -> list:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        rows = db.query(Metric).filter(Metric.run_id == run_id).all()
        return sorted(
            (
                [
                    row.split.value,
                    row.level.value,
                    row.name,
                    row.step,
                    row.fold_index,
                    row.inner_fold_index,
                    row.value,
                    row.std_value,
                ]
                for row in rows
            ),
            key=lambda r: [str(x) for x in r[:6]],
        )


def _split_indexes(client: TestClient, run_id: int) -> dict:
    return json.loads(_get(client, Run, run_id).split_indexes)


def _saved_dataset(path: str) -> dict:
    dataset = load_dataset(str(Path(path) / "dataset"))
    return {
        "columns": dataset.column_names,
        "types": {
            name: (
                dashai_type.to_string()
                if hasattr(dashai_type, "to_string")
                else type(dashai_type).__name__
            )
            for name, dashai_type in dataset.types.items()
        },
        "schema_metadata": {
            k.decode(): v.decode()
            for k, v in (dataset.arrow_table.schema.metadata or {}).items()
            if k != b"huggingface"
        },
        "rows": dataset.arrow_table.to_pydict(),
    }


def _predict_split(client: TestClient, run_id: int, dataset_id: int, split: str):
    response = client.post(
        "/api/v1/predict/",
        json={"run_id": run_id, "dataset_id": dataset_id, "split": split},
    )
    assert response.status_code == 200, response.text
    prediction_id = response.json()["id"]
    PredictJob(prediction_id=prediction_id).run()
    prediction = _get(client, Prediction, prediction_id)
    assert prediction.status == PredictionStatus.FINISHED
    return _saved_dataset(prediction.results_path)


def _preview(client: TestClient, run_id: int, rows: list):
    response = client.post(
        "/api/v1/predict/preview",
        data={"run_id": str(run_id), "manual_input_data": json.dumps(rows)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _explain(client: TestClient, run_id: int, name: str, parameters: dict):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        explainer = GlobalExplainer(
            name=name,
            run_id=run_id,
            explainer_name="PermutationFeatureImportance",
            parameters=parameters,
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id
    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "ExplainerJob",
            "kwargs": json.dumps(
                {"explainer_id": explainer_id, "explainer_scope": "global"}
            ),
        },
    )
    assert response.status_code == 201, response.text
    status = client.get(f"/api/v1/job/status/{response.json()['id']}").json()
    assert status["status"] == "finished", status
    with open(_get(client, GlobalExplainer, explainer_id).explanation_path, "rb") as f:
        return pickle.load(f)


def _package(client: TestClient, run_id: int, tmp_path: Path, rows: list) -> dict:
    destination = tmp_path / f"run-{run_id}.dashai-model"
    build_package(
        run_id,
        destination,
        client.app.container["session_factory"],
        client.app.container["component_registry"],
    )
    packaged = load_model(destination)
    info = packaged.info
    return {
        "input_columns": info["input_columns"],
        "output_columns": info["output_columns"],
        "predictions": packaged.predict(rows),
    }


def _iris_rows(columns: list, n_rows: int) -> list:
    """``n_rows`` rows taken across the file, so every species shows up."""
    frame = pd.read_csv(IRIS_CSV)
    positions = np.linspace(0, len(frame) - 1, n_rows).round().astype(int)
    return frame.iloc[positions][columns].to_dict(orient="records")


# --------------------------------------------------------------------------- #
# Tabular scenarios: real models, exact values
# --------------------------------------------------------------------------- #

SCENARIOS = {
    "classification_holdout": {
        "task": "TabularClassificationTask",
        "inputs": IRIS_FEATURES,
        "outputs": ["Species"],
        "model": ("KNeighborsClassifier", KNN),
        "metrics": CLASSIFICATION_METRICS,
    },
    "regression_holdout": {
        "task": "RegressionTask",
        "inputs": ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "Species"],
        "outputs": ["PetalWidthCm"],
        "model": ("LinearRegression", {}),
        "metrics": REGRESSION_METRICS,
    },
    "classification_kfold": {
        "task": "TabularClassificationTask",
        "inputs": IRIS_FEATURES,
        "outputs": ["Species"],
        "model": ("KNeighborsClassifier", KNN),
        "metrics": CLASSIFICATION_METRICS,
        "strategy": "CrossValidationEvaluationStrategy",
        "splits": KFOLD,
    },
    "classification_preprocessing": {
        "task": "TabularClassificationTask",
        "inputs": ["SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
        "outputs": ["Species"],
        "refs": [
            {"kind": "raw", "name": "SepalWidthCm"},
            {"kind": "raw", "name": "PetalLengthCm"},
            {"kind": "raw", "name": "PetalWidthCm"},
            {"kind": "group", "step": 0},
        ],
        "preprocessing": [BINARIZER],
        "model": ("KNeighborsClassifier", KNN),
        "metrics": CLASSIFICATION_METRICS,
    },
    "regression_preprocessing": {
        "task": "RegressionTask",
        "inputs": ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm"],
        "outputs": ["PetalWidthCm"],
        "refs": [
            {"kind": "raw", "name": "SepalLengthCm"},
            {"kind": "raw", "name": "SepalWidthCm"},
            {"kind": "raw", "name": "PetalLengthCm"},
            {"kind": "group", "step": 0},
        ],
        "preprocessing": [ONE_HOT],
        "model": ("LinearRegression", {}),
        "metrics": REGRESSION_METRICS,
    },
}


@pytest.fixture(scope="module", name="trained")
def fixture_trained(client: TestClient, dataset_1: Dataset) -> dict:
    """One trained run per tabular scenario, trained once for the module."""
    trained = {}
    for key, scenario in SCENARIOS.items():
        session_id = _create_session(
            client,
            dataset_id=dataset_1.id,
            task=scenario["task"],
            name=f"column-roles-net-{key}",
            inputs=scenario["inputs"],
            outputs=scenario["outputs"],
            refs=scenario.get("refs"),
            preprocessing=scenario.get("preprocessing", ()),
            strategy=scenario.get("strategy", "HoldoutEvaluationStrategy"),
            splits=scenario.get("splits"),
            metrics=scenario["metrics"],
        )
        model, params = scenario["model"]
        trained[key] = {
            "session_id": session_id,
            "run_id": _train(client, session_id, model, params),
        }
    return trained


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_the_session_stores_the_columns_it_was_given(client, trained, golden, key):
    session = _get(client, ModelSession, trained[key]["session_id"])
    _pin(golden, f"{key}/stored_columns", _stored_columns(session))


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_the_run_partitions_the_same_rows(client, trained, golden, key):
    _pin(golden, f"{key}/split_indexes", _split_indexes(client, trained[key]["run_id"]))


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_the_run_scores_the_same(client, trained, golden, key):
    _pin(golden, f"{key}/metrics", _metrics(client, trained[key]["run_id"]))


@pytest.mark.parametrize(
    "key",
    [k for k, s in SCENARIOS.items() if s.get("strategy") is None],
)
def test_a_prediction_on_the_test_partition_saves_the_same_file(
    client, dataset_1, trained, golden, key
):
    saved = _predict_split(client, trained[key]["run_id"], dataset_1.id, "test")
    _pin(golden, f"{key}/test_prediction", saved)


@pytest.mark.parametrize(
    ("key", "columns"),
    [
        ("classification_holdout", IRIS_FEATURES),
        ("regression_holdout", SCENARIOS["regression_holdout"]["inputs"]),
        ("classification_preprocessing", IRIS_FEATURES),
        (
            "regression_preprocessing",
            ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "Species"],
        ),
    ],
)
def test_the_manual_prediction_preview_is_the_same(
    client, trained, golden, key, columns
):
    preview = _preview(client, trained[key]["run_id"], _iris_rows(columns, 5))
    _pin(golden, f"{key}/preview", preview)


@pytest.mark.parametrize(
    ("key", "scoring"),
    # PermutationFeatureImportance only scores classifiers.
    [
        ("classification_holdout", "accuracy"),
        ("classification_preprocessing", "balanced_accuracy"),
    ],
)
def test_a_global_explanation_is_the_same(client, trained, golden, key, scoring):
    explanation = _explain(
        client,
        trained[key]["run_id"],
        f"column-roles-net-pfi-{key}",
        {"scoring": scoring, "n_repeats": 3, "random_state": 0},
    )
    _pin(golden, f"{key}/explanation", explanation)


@pytest.mark.parametrize(
    ("key", "columns"),
    [
        ("classification_holdout", IRIS_FEATURES),
        ("regression_holdout", SCENARIOS["regression_holdout"]["inputs"]),
        ("classification_preprocessing", IRIS_FEATURES),
    ],
)
def test_an_exported_package_is_the_same(
    client, trained, golden, tmp_path, key, columns
):
    package = _package(
        client, trained[key]["run_id"], tmp_path, _iris_rows(columns, 10)
    )
    _pin(golden, f"{key}/package", package)


# --------------------------------------------------------------------------- #
# Text, image and translation: the columns a model is handed
# --------------------------------------------------------------------------- #

RECORDED_EVENTS: list = []


def _column_summary(dataset) -> dict:
    """Every column's values, with images and bytes reduced to a digest."""
    summary = {}
    for name in dataset.column_names:
        values = []
        for value in dataset.arrow_table[name].to_pylist():
            if isinstance(value, dict) and "bytes" in value:
                value = {"path": value.get("path"), "bytes": value.get("bytes")}
            values.append(value)
        summary[name] = values
    return summary


class RecordingModel(BaseModel):
    """Records the columns and values it is trained and asked to predict on.

    It predicts the first class for classification (as probabilities, the way
    DashAI classifiers answer) and a fixed string for translation.
    """

    COMPATIBLE_COMPONENTS = [
        "TextClassificationTask",
        "ImageClassificationTask",
        "TranslationTask",
    ]

    def __init__(self, **kwargs):
        self.n_classes = None

    def save(self, filename):
        joblib.dump({"n_classes": self.n_classes}, filename)

    @classmethod
    def load(cls, filename):
        # ModelJob's loader calls it on an instance, PredictJob's on the class.
        model = cls()
        model.n_classes = joblib.load(filename)["n_classes"]
        return model

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        output = y_train.column_names[0]
        output_type = y_train.types.get(output)
        self.n_classes = (
            output_type.num_categories()
            if hasattr(output_type, "num_categories")
            else None
        )
        RECORDED_EVENTS.append(
            {
                "event": "train",
                "x": _column_summary(x_train),
                "y": _column_summary(y_train),
                "x_validation": (
                    None if x_validation is None else _column_summary(x_validation)
                ),
                "y_validation": (
                    None if y_validation is None else _column_summary(y_validation)
                ),
            }
        )
        return self

    def predict(self, x):
        RECORDED_EVENTS.append({"event": "predict", "x": _column_summary(x)})
        if self.n_classes is None:
            return ["translated"] * x.num_rows
        probabilities = np.zeros((x.num_rows, self.n_classes))
        probabilities[:, 0] = 1.0
        return probabilities


@pytest.fixture(scope="module", name="recording_model")
def fixture_recording_model(client: TestClient):
    registry = client.app.container["component_registry"]
    registry.register_component(RecordingModel)
    yield RecordingModel
    registry.unregister_component(RecordingModel)


def _text_csv(directory: Path) -> Path:
    path = directory / "texts.csv"
    pd.DataFrame(
        {
            "text": [
                f"sample number {i} says {'yes' if i % 2 else 'no'}" for i in range(20)
            ],
            "label": ["positive" if i % 2 else "negative" for i in range(20)],
        }
    ).to_csv(path, index=False)
    return path


def _translation_csv(directory: Path) -> Path:
    path = directory / "pairs.csv"
    pd.DataFrame(
        {
            "source": [f"the house number {i}" for i in range(20)],
            "target": [f"la casa numero {i}" for i in range(20)],
        }
    ).to_csv(path, index=False)
    return path


def _image_zip(directory: Path) -> Path:
    from PIL import Image

    path = directory / "images.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for label, colour in (("cats", (200, 30, 30)), ("dogs", (30, 30, 200))):
            for i in range(10):
                buffer = BytesIO()
                pixel = (colour[0], colour[1] + i, colour[2])
                Image.new("RGB", (2, 2), pixel).save(buffer, format="PNG")
                archive.writestr(
                    f"images/{label}/{label}_{i:02d}.png", buffer.getvalue()
                )
    return path


WIRING = {
    "text": {
        "task": "TextClassificationTask",
        "file": _text_csv,
        "params": {
            "dataloader": "CSVDataLoader",
            "separator": ",",
            "inferred_types": {
                "text": {"type": "Text", "dtype": "string"},
                "label": {"type": "Categorical", "dtype": "string"},
            },
        },
        "inputs": ["text"],
        "outputs": ["label"],
    },
    "image": {
        "task": "ImageClassificationTask",
        "file": _image_zip,
        "params": {"dataloader": "ImageDataLoader"},
        "inputs": ["image"],
        "outputs": ["label"],
    },
    "translation": {
        "task": "TranslationTask",
        "file": _translation_csv,
        "params": {
            "dataloader": "CSVDataLoader",
            "separator": ",",
            "inferred_types": {
                "source": {"type": "Text", "dtype": "string"},
                "target": {"type": "Text", "dtype": "string"},
            },
        },
        "inputs": ["source"],
        "outputs": ["target"],
    },
}


@pytest.mark.parametrize("key", list(WIRING))
def test_a_task_hands_the_model_the_same_columns(
    client, recording_model, golden, tmp_path, key
):
    wiring = WIRING[key]
    dataset_id = _create_dataset(
        client,
        wiring["file"](tmp_path),
        f"column-roles-net-{key}",
        wiring["params"],
    )
    session_id = _create_session(
        client,
        dataset_id=dataset_id,
        task=wiring["task"],
        name=f"column-roles-net-{key}",
        inputs=wiring["inputs"],
        outputs=wiring["outputs"],
    )
    RECORDED_EVENTS.clear()
    run_id = _train(client, session_id, "RecordingModel", {})
    trained_with = list(RECORDED_EVENTS)

    RECORDED_EVENTS.clear()
    saved = _predict_split(client, run_id, dataset_id, "test")

    _pin(
        golden,
        f"wiring/{key}",
        {
            "stored_columns": _stored_columns(_get(client, ModelSession, session_id)),
            "split_indexes": _split_indexes(client, run_id),
            "training": trained_with,
            "prediction": list(RECORDED_EVENTS),
            "saved": {"columns": saved["columns"], "types": saved["types"]},
        },
    )
