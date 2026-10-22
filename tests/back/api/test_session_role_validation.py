"""The API refuses a session whose columns do not fit its task's roles.

The structure of a session is the API's to check (the job trusts it): every
role named must be one the task declares, a protected role takes original
columns only, and every role gets columns of its types and in its number,
counted at the final stage, after the session's preprocessing. The same check
answers the wizard's ``/validation`` and guards ``PATCH`` when the task
changes.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures from this package's ``conftest.py``.
"""

import json

from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset

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
TO_TEXT = {
    "converter": "TypeCast",
    "params": {"new_type": "Text", "on_error": "raise"},
    "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
}


def _raw(*names):
    return [{"kind": "raw", "name": name} for name in names]


def _post(
    client,
    dataset_id,
    name,
    column_roles,
    task="TabularClassificationTask",
    preprocessing=(),
    strategy="HoldoutEvaluationStrategy",
    splits=None,
):
    return client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": task,
            "name": name,
            "column_roles": column_roles,
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": strategy,
            "splits": json.dumps(HOLDOUT if splits is None else splits),
            "preprocessing": list(preprocessing),
        },
    )


def _validate(
    client,
    dataset_id,
    column_roles,
    task="TabularClassificationTask",
    preprocessing=None,
):
    response = client.post(
        "/api/v1/model-session/validation",
        json={
            "task_name": task,
            "dataset_id": dataset_id,
            "column_roles": column_roles,
            "preprocessing": preprocessing,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_a_role_the_task_does_not_declare_is_refused(
    client: TestClient, dataset_1: Dataset
):
    response = _post(
        client,
        dataset_1.id,
        "unknown role",
        {
            "features": _raw(*IRIS_FEATURES),
            "target": _raw("Species"),
            "index": _raw("SepalLengthCm"),
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "TabularClassificationTask has no column role 'index'. Its roles are: "
        "features, target."
    )


def test_a_required_role_left_empty_is_refused(client: TestClient, dataset_1):
    response = _post(
        client, dataset_1.id, "no target", {"features": _raw(*IRIS_FEATURES)}
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "Output cardinality (0) does not match task cardinality (1)"
    )


def test_a_protected_role_takes_no_converter_output(client: TestClient, dataset_1):
    response = _post(
        client,
        dataset_1.id,
        "protected group",
        {
            "features": _raw("SepalWidthCm"),
            "target": [{"kind": "group", "step": 0}],
        },
        preprocessing=[TO_TEXT],
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "The 'target' role of TabularClassificationTask is protected from the "
        "preprocessing: it takes original columns only."
    )


def test_a_column_of_a_type_the_role_does_not_take_is_refused(
    client: TestClient, dataset_1
):
    response = _post(
        client,
        dataset_1.id,
        "categorical feature for clustering",
        {"features": _raw("SepalLengthCm", "Species")},
        task="ClusteringTask",
        strategy="FullDatasetEvaluationStrategy",
        splits={},
    )

    assert response.status_code == 422, response.text
    assert "is not an allowed type for input columns." in response.json()["detail"]


def test_too_many_columns_for_a_role_are_refused(client: TestClient, dataset_1):
    response = _post(
        client,
        dataset_1.id,
        "two targets",
        {"features": _raw("SepalLengthCm"), "target": _raw("Species", "Species")},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "Output cardinality (2) does not match task cardinality (1)"
    )


def test_a_converter_output_is_checked_at_the_final_stage(
    client: TestClient, dataset_1
):
    """SepalLengthCm cast to Text is no longer a type the features take."""
    response = _post(
        client,
        dataset_1.id,
        "text feature after the cast",
        {
            "features": [{"kind": "raw", "name": "SepalLengthCm"}],
            "target": _raw("Species"),
        },
        preprocessing=[TO_TEXT],
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == (
        "Text is not an allowed type for input columns."
    )


def test_validation_answers_with_the_same_check(client: TestClient, dataset_1):
    assert _validate(client, dataset_1.id, {"features": _raw(*IRIS_FEATURES)}) == {
        "dataset_status": "invalid",
        "error": "Output cardinality (0) does not match task cardinality (1)",
    }
    assert _validate(
        client,
        dataset_1.id,
        {"features": _raw(*IRIS_FEATURES), "target": _raw("Species")},
    ) == {"dataset_status": "valid"}


def test_validation_counts_converter_outputs_as_inputs(client: TestClient, dataset_1):
    """A group ref counts towards its role, so a task taking exactly one input
    can be fed a converter's output."""
    binarizer = {
        "converter": "Binarizer",
        "params": {"threshold": 3.0},
        "scope": [{"kind": "raw", "name": "SepalLengthCm"}],
    }
    assert _validate(
        client,
        dataset_1.id,
        {
            "features": [{"kind": "group", "step": 0}],
            "target": _raw("Species"),
        },
        preprocessing=[binarizer],
    ) == {"dataset_status": "valid"}


def test_changing_the_task_rechecks_the_columns(client: TestClient, dataset_1):
    created = _post(
        client,
        dataset_1.id,
        "classification to regression",
        {"features": _raw(*IRIS_FEATURES), "target": _raw("Species")},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/model-session/{session_id}",
        params={"task_name": "RegressionTask"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"].startswith(
        "The session's columns do not fit task RegressionTask: "
    )
    assert response.json()["detail"].endswith(
        "is not an allowed type for output columns."
    )
