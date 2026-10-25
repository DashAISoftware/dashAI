"""One way to resolve a session's task, and one way to say it cannot be.

A session's task can fail to be built in two ways: it is not registered (a
plugin that was uninstalled), or it is registered and its constructor raises
(a broken plugin). The endpoints and the prediction job used to resolve it
four different ways, with different texts and statuses, and the prediction
reported a constructor that raised as "not found". Now there is one
function: not registered is a 404 "Task X not found in the registry.", and a
constructor that raised is a 500 that says so and gives its cause. The jobs
report the same texts.

Also here: a column reference that does not exist after the preprocessing is
reported in words, not as the bare code ``missing_ref``.
"""

import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import ModelSession, Prediction, Run
from DashAI.back.job.base_job import JobError
from DashAI.back.job.predict_job import PredictJob
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask
from tests.back.session_columns import xy_roles

BUILT_WRONG = "Task BrokenPluginTask could not be built: the plugin is broken"


class BrokenPluginTask(TabularClassificationTask):
    """A registered task whose constructor raises, like a broken plugin."""

    def __init__(self):
        raise RuntimeError("the plugin is broken")


@pytest.fixture(scope="module", name="run_id")
def fixture_run_id(client: TestClient, dataset_1) -> int:
    client.app.container["component_registry"].register_component(BrokenPluginTask)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = ModelSession(
            dataset_id=dataset_1.id,
            name="session of a broken task",
            task_name="BrokenPluginTask",
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
            name="run of a broken task",
        )
        db.add(run)
        db.commit()
        return run.id


def test_filter_datasets_says_the_task_could_not_be_built(client, run_id):
    response = client.get("/api/v1/predict/filter_datasets", params={"run_id": run_id})

    assert response.status_code == 500, response.text
    assert response.json() == {"detail": BUILT_WRONG}


def test_valid_datasets_says_the_task_could_not_be_built(client, run_id):
    response = client.post(
        "/api/v1/explainer/local/valid-datasets", json={"run_id": run_id}
    )

    assert response.status_code == 500, response.text
    assert response.json() == {"detail": BUILT_WRONG}


def test_validate_dataset_says_the_task_could_not_be_built(client, run_id, dataset_1):
    response = client.post(
        "/api/v1/explainer/local/validate-dataset",
        json={"run_id": run_id, "dataset_id": dataset_1.id},
    )

    assert response.status_code == 500, response.text
    assert response.json() == {"detail": BUILT_WRONG}


def test_the_preview_says_the_task_could_not_be_built(client, run_id):
    response = client.post(
        "/api/v1/predict/preview",
        data={
            "run_id": str(run_id),
            "manual_input_data": json.dumps([{"SepalLengthCm": 5.0}]),
        },
    )

    assert response.status_code == 500, response.text
    assert response.json() == {"detail": BUILT_WRONG}


def test_the_prediction_job_says_the_task_could_not_be_built(client, run_id):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        prediction = Prediction(run_id=run_id, dataset_id=None)
        db.add(prediction)
        db.commit()
        prediction_id = prediction.id

    with pytest.raises(JobError) as raised:
        PredictJob(
            prediction_id=prediction_id,
            manual_input_data=[{"SepalLengthCm": 5.0}],
        ).run()

    assert str(raised.value) == BUILT_WRONG


def test_a_reference_missing_after_the_preprocessing_is_said_in_words(
    client: TestClient, dataset_1
):
    """A scaler rewrites its columns in place and adds none, so a reference
    to its output group points at nothing."""
    response = client.post(
        "/api/v1/model-session/validation",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "column_roles": {
                "features": [{"kind": "group", "step": 0}],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "preprocessing": [
                {
                    "converter": "StandardScaler",
                    "params": {},
                    "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "dataset_status": "invalid",
        "error": (
            "The 'features' role takes the output of step 1, which does not "
            "exist after the preprocessing."
        ),
    }
