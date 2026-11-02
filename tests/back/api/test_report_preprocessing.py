"""A report over a session that preprocesses sees the rows the model saw.

The model of such a session is trained on the columns its fitted converters
produce, so a report has to prepare the raw rows with the raw refs, as
training does, and run them through the session's fitted preprocessor before
predicting, as ``PredictJob`` does. Two converters cover the two ways of
getting it wrong: one that adds columns (a Binarizer, whose ``bin_*`` columns
the raw dataset does not have) and one that rewrites its columns in place (a
StandardScaler, whose output keeps the raw names, so predicting on the raw
values would not fail, only be wrong).

The report's accuracy on each partition has to match the one training
measured on it. That includes the rows: a step that removes rows from every
partition (NanRemover) removed them before training measured it.
"""

import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.enums.status import ReportStatus, RunStatus
from DashAI.back.dependencies.database.models import (
    Dataset,
    Metric,
    Report,
    Run,
)
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.report_job import ReportJob
from tests.back.api.test_session_nan_remover import (  # noqa: F401
    create_incomplete_dataset,
)

FEATURES = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
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
RAW_FEATURES = [{"kind": "raw", "name": name} for name in FEATURES]
#: converter -> (params, the features the session picks). The Binarizer's
#: output is a group of new columns; the scaler's is its scope, renamed to
#: nothing, so its scaled columns are picked by their raw names.
CONVERTERS = {
    "Binarizer": ({"threshold": 3.0}, [{"kind": "group", "step": 0}]),
    "StandardScaler": ({}, RAW_FEATURES),
}
PARTITIONS = {"Train": SplitEnum.TRAIN, "Test": SplitEnum.TEST}


def _train(client: TestClient, dataset: Dataset, converter: str) -> int:
    return _train_session(
        client,
        dataset,
        name=f"report-preprocessing-{converter}",
        features=CONVERTERS[converter][1],
        target="Species",
        step={
            "converter": converter,
            "params": CONVERTERS[converter][0],
            "scope": RAW_FEATURES,
        },
        model=("DecisionTreeClassifier", {"random_state": 0}),
    )


def _train_session(
    client: TestClient,
    dataset: Dataset,
    name: str,
    features: list,
    target: str,
    step: dict,
    model: tuple,
) -> int:
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset.id,
            "task_name": "TabularClassificationTask",
            "name": name,
            "column_roles": {
                "features": features,
                "target": [{"kind": "raw", "name": target}],
            },
            "train_metrics": ["Accuracy"],
            "validation_metrics": ["Accuracy"],
            "test_metrics": ["Accuracy"],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT),
            "preprocessing": [step],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["preprocessing_status"] == "ready", response.text
    model_name, parameters = model
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": response.json()["id"],
            "model_name": model_name,
            "name": f"{model_name} in {name}",
            "parameters": parameters,
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
    with client.app.container["session_factory"]() as db:
        assert db.get(Run, run_id).status == RunStatus.FINISHED
    return run_id


def _trained_accuracy(client: TestClient, run_id: int, split: SplitEnum) -> float:
    with client.app.container["session_factory"]() as db:
        row = (
            db.query(Metric)
            .filter(
                Metric.run_id == run_id,
                Metric.name == "Accuracy",
                Metric.split == split,
                Metric.level == LevelEnum.LAST,
            )
            .one()
        )
        return row.value


def _report_accuracies(client: TestClient, run_id: int) -> dict:
    response = client.post(
        "/api/v1/report/",
        json={"run_id": run_id, "report_name": "ConfusionMatrix", "parameters": {}},
    )
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]

    ReportJob(report_id=report_id).run()

    with client.app.container["session_factory"]() as db:
        assert db.get(Report, report_id).status == ReportStatus.FINISHED
    artifacts = client.get(f"/api/v1/report/{report_id}/artifacts").json()
    accuracies = {}
    for group in artifacts[0]["groups"]:
        grid = json.loads(group["artifacts"][0]["payload"])["data"][0]["z"]
        correct = sum(grid[i][i] for i in range(len(grid)))
        accuracies[group["title"]] = correct / sum(map(sum, grid))
    return accuracies


@pytest.mark.parametrize("converter", sorted(CONVERTERS))
def test_the_report_predicts_on_the_rows_the_model_was_trained_on(
    client: TestClient, dataset_1: Dataset, converter: str
):
    run_id = _train(client, dataset_1, converter)

    accuracies = _report_accuracies(client, run_id)

    for title, split in PARTITIONS.items():
        assert accuracies[title] == pytest.approx(
            _trained_accuracy(client, run_id, split)
        ), title


def test_the_report_leaves_out_the_rows_nan_remover_removed_in_training(
    client: TestClient, incomplete_dataset: Dataset
):
    # KNN cannot take a missing value, so the report only finishes if it
    # removed the incomplete rows of each partition, as training did.
    raw = [{"kind": "raw", "name": "age"}, {"kind": "raw", "name": "height"}]
    run_id = _train_session(
        client,
        incomplete_dataset,
        name="report-preprocessing-NanRemover",
        features=raw,
        target="label",
        step={"converter": "NanRemover", "params": {}, "scope": raw},
        model=("KNeighborsClassifier", {"n_neighbors": 3}),
    )

    accuracies = _report_accuracies(client, run_id)

    for title, split in PARTITIONS.items():
        assert accuracies[title] == pytest.approx(
            _trained_accuracy(client, run_id, split)
        ), title
