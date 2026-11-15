"""What the frontend reads from the backend for the x/y tasks, before PR 4.

PR 4 makes the frontend read declarations instead of deciding on its own, and
adds declarations for it to read. This net pins what the x/y tasks already
publish, so the PR can add keys without changing the ones the frontend reads:

- the metrics offered to each x/y task, in order: the first one is the goal
  metric the run dialog selects by default;
- the metadata of every task, evaluation strategy and splitter, compared as a
  subset, so a new key is allowed and a changed or removed one is not;
- the run payloads the frontend sends for an x/y session.

Recorded on ``e333ba475`` with ``DASHAI_RECORD_FRONT_DECLARATIONS_NET=1``.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.tasks.forecasting_task import ForecastingTask

GOLDEN_PATH = Path(__file__).with_name("front_declarations_net_golden.json")
RECORDING = os.environ.get("DASHAI_RECORD_FRONT_DECLARATIONS_NET") == "1"


@pytest.fixture(scope="module", name="golden")
def fixture_golden():
    if RECORDING:
        recorded = {}
        yield recorded
        GOLDEN_PATH.write_text(
            json.dumps(recorded, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        yield json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _components(client: TestClient, **params):
    response = client.get("/api/v1/component/", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _xy_task_names(client: TestClient):
    registry = client.app.container["component_registry"]
    return sorted(
        component["name"]
        for component in registry.get_components_by_types(select="Task")
        if issubclass(component["class"], BaseTask)
        and not issubclass(component["class"], ForecastingTask)
    )


def test_the_metrics_offered_to_each_xy_task_in_order(client: TestClient, golden):
    offered = {
        task: [
            metric["name"]
            for metric in _components(
                client, select_types="Metric", related_component=task
            )
        ]
        for task in _xy_task_names(client)
    }

    if RECORDING:
        golden["metrics"] = offered
        return
    assert offered == golden["metrics"]


@pytest.mark.parametrize("component_type", ["Task", "EvaluationStrategy", "Splitter"])
def test_the_metadata_the_frontend_reads_keeps_its_keys(
    client: TestClient, golden, component_type: str
):
    metadata = {
        component["name"]: component["metadata"]
        for component in _components(client, select_types=component_type)
    }
    if component_type == "Task":
        xy = set(_xy_task_names(client))
        metadata = {name: value for name, value in metadata.items() if name in xy}

    if RECORDING:
        golden.setdefault("metadata", {})[component_type] = metadata
        return
    expected = golden["metadata"][component_type]
    assert set(metadata) == set(expected)
    for name, recorded in expected.items():
        current = {key: metadata[name].get(key) for key in recorded}
        assert current == recorded, name


IRIS_ROLES = {
    "features": [
        {"kind": "raw", "name": "SepalLengthCm"},
        {"kind": "raw", "name": "SepalWidthCm"},
        {"kind": "raw", "name": "PetalLengthCm"},
    ],
}
HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "splitType": "random",
    "train": 0.6,
    "validation": 0.2,
    "test": 0.2,
}


def _session(client: TestClient, dataset_id: int, task_name: str, target: str):
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": task_name,
            "name": f"front declarations {task_name}",
            "column_roles": {
                **IRIS_ROLES,
                "target": [{"kind": "raw", "name": target}],
            },
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture(scope="module", name="sessions")
def fixture_sessions(client: TestClient, dataset_1):
    sessions = {
        "TabularClassificationTask": _session(
            client, dataset_1.id, "TabularClassificationTask", "Species"
        ),
        "RegressionTask": _session(
            client, dataset_1.id, "RegressionTask", "PetalWidthCm"
        ),
    }
    yield sessions
    for session_id in sessions.values():
        client.delete(f"/api/v1/model-session/{session_id}")


OPTUNA = {
    "optimizer_name": "OptunaOptimizer",
    "optimizer_parameters": {"n_trials": 2, "sampler": "TPESampler", "pruner": "None"},
}
NO_OPTIMIZER = {"optimizer_name": "", "optimizer_parameters": {}}


@pytest.mark.parametrize(
    ("task_name", "model_name", "optimizer", "goal_metric"),
    [
        ("TabularClassificationTask", "KNeighborsClassifier", OPTUNA, "Accuracy"),
        ("TabularClassificationTask", "KNeighborsClassifier", NO_OPTIMIZER, "F1"),
        ("TabularClassificationTask", "KNeighborsClassifier", NO_OPTIMIZER, ""),
        ("RegressionTask", "LinearRegression", OPTUNA, "MAE"),
        ("RegressionTask", "LinearRegression", NO_OPTIMIZER, "RMSE"),
    ],
)
def test_the_run_payloads_the_frontend_sends_are_accepted(
    client: TestClient, sessions, task_name, model_name, optimizer, goal_metric
):
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": sessions[task_name],
            "model_name": model_name,
            "name": f"{model_name} {goal_metric or 'no goal'}",
            "parameters": {},
            **optimizer,
            "goal_metric": goal_metric,
            "description": "",
            # api/run.ts sends them, always empty: the job writes the plots.
        },
    )

    assert response.status_code == 201, response.text
