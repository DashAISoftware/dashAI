"""POST and PATCH /run/ check the goal metric against the session's task.

The run dialog lists the metrics the task offers, and offers to optimize only
the ones that can be. The API took any string until PR 4, and the job found
out: a metric of another task as "not compatible with the Task" after the run
was queued, and interval coverage as the optimization goal only once a search
began. The API refuses both now; the job keeps its own guard for runs that do
not come through it.
"""

import json

import pytest
from fastapi.testclient import TestClient

from tests.back.api.test_forecasting_acceptance import _monthly, _session

OPTUNA = {
    "optimizer_name": "OptunaOptimizer",
    "optimizer_parameters": {"n_trials": 2, "sampler": "TPESampler", "pruner": "None"},
}
NO_OPTIMIZER = {"optimizer_name": "", "optimizer_parameters": {}}


def _run(client: TestClient, session_id, model, goal_metric, optimizer):
    return client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session_id,
            "model_name": model,
            "name": f"{model} {goal_metric or 'no goal'}",
            "parameters": {},
            **optimizer,
            "goal_metric": goal_metric,
            "description": "",
            "plot_history_path": "",
            "plot_slice_path": "",
            "plot_contour_path": "",
            "plot_importance_path": "",
        },
    )


@pytest.fixture(scope="module", name="classification")
def fixture_classification(client: TestClient, dataset_1):
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "goal metric classification",
            "column_roles": {
                "features": [{"kind": "raw", "name": "SepalLengthCm"}],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(
                {
                    "splitter_name": "HoldoutSplitter",
                    "train": 0.6,
                    "validation": 0.2,
                    "test": 0.2,
                }
            ),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture(scope="module", name="forecasting")
def fixture_forecasting(client: TestClient, tmp_path_factory):
    return _session(client, tmp_path_factory.mktemp("goal-metric"), _monthly())


def test_a_metric_the_task_does_not_offer_is_refused(client, classification):
    response = _run(client, classification, "KNeighborsClassifier", "MAE", OPTUNA)

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "Metric 'MAE' is not available for task TabularClassificationTask."
    )


def test_a_metric_that_cannot_be_optimized_is_refused_as_the_goal_of_a_search(
    client, forecasting
):
    response = _run(
        client, forecasting, "SeasonalNaiveForecaster", "IntervalCoverage", OPTUNA
    )

    assert response.status_code == 422, response.text
    assert "IntervalCoverage cannot be optimized" in response.json()["detail"]


def test_a_metric_that_cannot_be_optimized_is_fine_without_a_search(
    client, forecasting
):
    response = _run(
        client, forecasting, "NaiveForecaster", "IntervalCoverage", NO_OPTIMIZER
    )

    assert response.status_code == 201, response.text


def test_a_search_needs_a_goal_metric(client, classification):
    response = _run(client, classification, "KNeighborsClassifier", "", OPTUNA)

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "A run that searches with OptunaOptimizer needs a goal metric to optimize."
    )


def test_a_patch_is_checked_on_the_run_it_leaves(client, forecasting):
    created = _run(client, forecasting, "SeasonalNaiveForecaster", "MAE", OPTUNA)
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]

    url = f"/api/v1/run/{run_id}"
    goal = client.patch(url, json={"goal_metric": "IntervalCoverage"})
    other_task = client.patch(url, json={"goal_metric": "Accuracy"})

    assert goal.status_code == 422, goal.text
    assert "IntervalCoverage cannot be optimized" in goal.json()["detail"]
    assert other_task.status_code == 422, other_task.text
    assert client.get(f"/api/v1/run/{run_id}").json()["goal_metric"] == "MAE"


def test_a_patch_that_adds_a_search_checks_the_goal_it_finds(client, forecasting):
    created = _run(
        client, forecasting, "NaiveForecaster", "IntervalCoverage", NO_OPTIMIZER
    )
    run_id = created.json()["id"]

    url = f"/api/v1/run/{run_id}"
    response = client.patch(url, json={"optimizer": "OptunaOptimizer"})

    assert response.status_code == 422, response.text
    assert client.get(f"/api/v1/run/{run_id}").json()["optimizer_name"] == ""
