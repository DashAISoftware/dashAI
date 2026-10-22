"""A session stores its columns by role, and its task reads them back.

``POST /model-session/`` stores the refs it is given per role, and
``PreprocessingJob`` the columns the fitted chain resolved. ``session_io``
reads the roles back as a model's inputs and outputs through the task. The
old fields are refused.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures from this package's ``conftest.py``.
"""

import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import ModelSession
from DashAI.back.preprocessing.column_ref import parse_column_refs
from DashAI.back.tasks.session_roles import session_io

IRIS_FEATURES = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
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
BINARIZER = {
    "converter": "Binarizer",
    "params": {"threshold": 3.0},
    "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
}


def _create(client: TestClient, body: dict) -> ModelSession:
    payload = {
        "train_metrics": [],
        "validation_metrics": [],
        "test_metrics": [],
        "preprocessing": [],
        **body,
    }
    response = client.post("/api/v1/model-session/", json=payload)
    assert response.status_code == 201, response.text
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        row = db.get(ModelSession, response.json()["id"])
        db.expunge(row)
        return row


def _task(client: TestClient, session: ModelSession):
    registry = client.app.container["component_registry"]
    return registry[session.task_name]["class"]()


RAW = [{"kind": "raw", "name": name} for name in IRIS_FEATURES]
BINARIZED = [
    {"kind": "raw", "name": "SepalWidthCm"},
    {"kind": "group", "step": 0},
]


@pytest.fixture(scope="module", name="plain")
def fixture_plain(client, dataset_1):
    return _create(
        client,
        {
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "column-roles-plain",
            "column_roles": {
                "features": [
                    {"kind": "raw", "name": column} for column in IRIS_FEATURES
                ],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT),
        },
    )


@pytest.fixture(scope="module", name="preprocessed")
def fixture_preprocessed(client, dataset_1):
    return _create(
        client,
        {
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "column-roles-preprocessed",
            "column_roles": {
                "features": [
                    {"kind": "raw", "name": "SepalWidthCm"},
                    {"kind": "group", "step": 0},
                ],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT),
            "preprocessing": [BINARIZER],
        },
    )


@pytest.fixture(scope="module", name="clustering")
def fixture_clustering(client, dataset_1):
    return _create(
        client,
        {
            "dataset_id": dataset_1.id,
            "task_name": "ClusteringTask",
            "name": "column-roles-clustering",
            "column_roles": {
                "features": [
                    {"kind": "raw", "name": "SepalLengthCm"},
                    {"kind": "raw", "name": "PetalLengthCm"},
                ],
                "target": [],
            },
            "evaluation_strategy": "FullDatasetEvaluationStrategy",
            "splits": json.dumps({}),
        },
    )


def test_a_session_without_preprocessing_stores_raw_refs_by_role(plain):
    assert plain.column_roles == {
        "features": {
            "refs": [{"kind": "raw", "name": column} for column in IRIS_FEATURES],
            "columns": IRIS_FEATURES,
        },
        "target": {
            "refs": [{"kind": "raw", "name": "Species"}],
            "columns": ["Species"],
        },
    }


def test_preprocessing_stores_the_columns_it_resolved(preprocessed):
    assert preprocessed.preprocessing_status == "ready"
    assert preprocessed.column_roles == {
        "features": {
            "refs": [
                {"kind": "raw", "name": "SepalWidthCm"},
                {"kind": "group", "step": 0, "slot": None, "name": None},
            ],
            "columns": ["SepalWidthCm", "bin_SepalLengthCm"],
        },
        "target": {
            "refs": [{"kind": "raw", "name": "Species"}],
            "columns": ["Species"],
        },
    }


def test_a_session_without_a_target_stores_no_target_role(clustering):
    assert set(clustering.column_roles) == {"features"}


@pytest.mark.parametrize(
    ("fixture", "inputs", "outputs", "refs", "raw_inputs"),
    [
        ("plain", IRIS_FEATURES, ["Species"], RAW, IRIS_FEATURES),
        (
            "preprocessed",
            ["SepalWidthCm", "bin_SepalLengthCm"],
            ["Species"],
            BINARIZED,
            ["SepalWidthCm"],
        ),
        (
            "clustering",
            ["SepalLengthCm", "PetalLengthCm"],
            [],
            RAW[:1] + [{"kind": "raw", "name": "PetalLengthCm"}],
            ["SepalLengthCm", "PetalLengthCm"],
        ),
    ],
)
def test_the_task_reads_the_roles_as_inputs_and_outputs(
    request, client, fixture, inputs, outputs, refs, raw_inputs
):
    session = request.getfixturevalue(fixture)
    io = session_io(session, _task(client, session))

    assert io.inputs == inputs
    assert io.outputs == outputs
    assert io.input_refs == parse_column_refs(refs)
    assert io.raw_inputs == raw_inputs


@pytest.mark.parametrize(
    ("endpoint", "old_body"),
    [
        (
            "/api/v1/model-session/",
            {
                "task_name": "TabularClassificationTask",
                "name": "old-payload",
                "input_columns": IRIS_FEATURES,
                "output_columns": ["Species"],
                "train_metrics": [],
                "validation_metrics": [],
                "test_metrics": [],
                "evaluation_strategy": "HoldoutEvaluationStrategy",
                "splits": json.dumps(HOLDOUT),
            },
        ),
        (
            "/api/v1/model-session/validation",
            {
                "task_name": "TabularClassificationTask",
                "inputs_columns": IRIS_FEATURES,
                "outputs_columns": ["Species"],
            },
        ),
        (
            "/api/v1/model-session/preprocessing/structure",
            {"candidates": IRIS_FEATURES, "output_columns": ["Species"]},
        ),
    ],
)
def test_the_old_column_fields_are_refused(client, dataset_1, endpoint, old_body):
    response = client.post(endpoint, json={"dataset_id": dataset_1.id, **old_body})

    assert response.status_code == 422, response.text
    refused = {error["loc"][-1] for error in response.json()["detail"]}
    assert refused & {
        "input_columns",
        "output_columns",
        "inputs_columns",
        "outputs_columns",
        "candidates",
    }
