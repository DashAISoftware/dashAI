"""The endpoints that read a session's columns refuse a task not registered.

A session stores its columns by role, and only its task can say which of them
feed the model. When the task is not in the registry, for instance a plugin
that was uninstalled, ``GET /predict/filter_datasets`` and the two explainer
endpoints that check datasets answer 404 naming the task. Before roles they
answered 200 from the stored input columns, and the prediction or the
explanation failed later, in its job.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures from this package's ``conftest.py``.
"""

import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import ModelSession, Run
from tests.back.session_columns import xy_roles

MISSING_TASK = "UninstalledPluginTask"
DETAIL = f"Task {MISSING_TASK} not found in the registry."


@pytest.fixture(scope="module", name="run_id")
def fixture_run_id(client: TestClient, dataset_1) -> int:
    """A run of a session whose task is not registered, written to the DB."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = ModelSession(
            dataset_id=dataset_1.id,
            name="session of an uninstalled task",
            task_name=MISSING_TASK,
            column_roles=xy_roles(["SepalLengthCm"], ["Species"]),
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits=json.dumps({}),
        )
        db.add(session)
        db.commit()
        run = Run(
            model_session_id=session.id,
            model_name="KNeighborsClassifier",
            parameters={},
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={},
            goal_metric="Accuracy",
            name="run of an uninstalled task",
        )
        db.add(run)
        db.commit()
        return run.id


def test_filter_datasets_names_the_missing_task(client: TestClient, run_id: int):
    response = client.get("/api/v1/predict/filter_datasets", params={"run_id": run_id})

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": DETAIL}


def test_valid_datasets_for_an_explanation_names_the_missing_task(
    client: TestClient, run_id: int
):
    response = client.post(
        "/api/v1/explainer/local/valid-datasets", json={"run_id": run_id}
    )

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": DETAIL}


def test_validating_a_dataset_for_an_explanation_names_the_missing_task(
    client: TestClient, run_id: int, dataset_1
):
    response = client.post(
        "/api/v1/explainer/local/validate-dataset",
        json={"run_id": run_id, "dataset_id": dataset_1.id},
    )

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": DETAIL}


def test_a_missing_run_is_still_reported_first(client: TestClient):
    response = client.get("/api/v1/predict/filter_datasets", params={"run_id": 999999})

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Run not found"}
