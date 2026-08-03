"""End to end tests for reports: creation, job, retrieval and cleanup.

Trains a real decision tree through the real ``ModelJob`` so the report
receives what a genuine run produces: a probability matrix from ``predict`` and
encoded targets from ``prepare_output``.
"""

import json

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import ReportStatus, RunStatus
from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader
from DashAI.back.dependencies.database.models import (
    Dataset,
    ModelSession,
    Report,
    Run,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import JobError
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.report_job import ReportJob
from DashAI.back.metrics.classification.accuracy import Accuracy
from DashAI.back.models.scikit_learn.decision_tree_classifier import (
    DecisionTreeClassifier,
)
from DashAI.back.optimizers.optuna_optimizer import OptunaOptimizer
from DashAI.back.reports.classification.confusion_matrix import ConfusionMatrix
from DashAI.back.reports.classification.per_class_breakdown import (
    PerClassBreakdown,
)
from DashAI.back.reports.classification.roc_curve import RocCurve
from DashAI.back.reports.regression.residual_plot import ResidualPlot
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask

INPUT_COLUMNS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
OUTPUT_COLUMNS = ["Species"]


@pytest.fixture(scope="module", name="test_registry", autouse=True)
def setup_test_registry(client):
    container = client.app.container
    sentinel = object()
    services = container._services
    old = services.get("component_registry", sentinel)

    services["component_registry"] = ComponentRegistry(
        initial_components=[
            TabularClassificationTask,
            DecisionTreeClassifier,
            Accuracy,
            CSVDataLoader,
            ModelJob,
            ReportJob,
            OptunaOptimizer,
            ConfusionMatrix,
            RocCurve,
            PerClassBreakdown,
            ResidualPlot,
        ]
    )
    yield services["component_registry"]
    if old is sentinel:
        del services["component_registry"]
    else:
        services["component_registry"] = old


@pytest.fixture(scope="module", name="model_session_id")
def create_model_session(client: TestClient, dataset_1: Dataset, test_registry):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_1.id,
            name="ReportsSession",
            task_name="TabularClassificationTask",
            input_columns=INPUT_COLUMNS,
            output_columns=OUTPUT_COLUMNS,
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            splits=json.dumps(
                {
                    "train": 0.5,
                    "test": 0.2,
                    "validation": 0.3,
                    "is_random": True,
                    "has_changed": True,
                    "seed": 42,
                    "shuffle": True,
                    "stratify": False,
                    "splitType": "random",
                }
            ),
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)

        yield model_session.id

        db.delete(model_session)
        db.commit()


@pytest.fixture(scope="module", name="trained_run_id")
def train_a_real_model(client: TestClient, model_session_id: int, test_registry):
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": model_session_id,
            "model_name": "DecisionTreeClassifier",
            "name": "ReportsRun",
            "parameters": {
                "criterion": "gini",
                "max_depth": 3,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "max_features": None,
                "class_weight": None,
            },
            "optimizer_name": "",
            "optimizer_parameters": {
                "n_trials": 1,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            "goal_metric": "",
            "description": "Run under report",
            "plot_history_path": "path/to/history.png",
            "plot_slice_path": "path/to/slice.png",
            "plot_contour_path": "path/to/contour.png",
            "plot_importance_path": "path/to/importance.png",
        },
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]

    ModelJob(run_id=run_id).run()
    with client.app.container["session_factory"]() as db:
        assert db.get(Run, run_id).status == RunStatus.FINISHED

    yield run_id

    client.delete(f"/api/v1/run/{run_id}")


def _create(client: TestClient, run_id: int, name: str, **overrides) -> int:
    body = {
        "run_id": run_id,
        "report_name": name,
        "parameters": {},
        "split": "test",
        **overrides,
    }
    response = client.post("/api/v1/report/", json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_lists_and_computes_a_confusion_matrix(
    client: TestClient, trained_run_id: int
):
    report_id = _create(client, trained_run_id, "ConfusionMatrix")

    listed = client.get(f"/api/v1/report/?run_id={trained_run_id}").json()
    assert any(item["id"] == report_id for item in listed)

    # Before the job runs there is nothing to show, but the row exists.
    assert client.get(f"/api/v1/report/{report_id}/artifacts").json() == []

    ReportJob(report_id=report_id).run()

    with client.app.container["session_factory"]() as db:
        assert db.get(Report, report_id).status == ReportStatus.FINISHED

    artifacts = client.get(f"/api/v1/report/{report_id}/artifacts").json()
    assert len(artifacts) == 1
    assert artifacts[0]["type"] == "plotly"
    figure = json.loads(artifacts[0]["payload"])
    # Class names come from the model's own output encoder.
    assert "Iris-setosa" in figure["data"][0]["x"]

    client.delete(f"/api/v1/report/{report_id}")


def test_roc_curve_runs_on_real_probabilities(client: TestClient, trained_run_id: int):
    """DashAI classifiers return a probability matrix from predict.

    That is what makes an ROC curve computable without any new model contract.
    """
    report_id = _create(client, trained_run_id, "RocCurve")

    ReportJob(report_id=report_id).run()

    artifacts = client.get(f"/api/v1/report/{report_id}/artifacts").json()
    figure = json.loads(artifacts[0]["payload"])
    assert any("AUC" in trace.get("name", "") for trace in figure["data"])

    client.delete(f"/api/v1/report/{report_id}")


def test_each_split_is_its_own_report(client: TestClient, trained_run_id: int):
    train_id = _create(client, trained_run_id, "PerClassBreakdown", split="train")
    test_id = _create(client, trained_run_id, "PerClassBreakdown", split="test")

    ReportJob(report_id=train_id).run()
    ReportJob(report_id=test_id).run()

    train_rows = client.get(f"/api/v1/report/{train_id}/artifacts").json()[0][
        "payload"
    ]["rows"]
    test_rows = client.get(f"/api/v1/report/{test_id}/artifacts").json()[0]["payload"][
        "rows"
    ]

    # Support is the row count of the split, so the two must disagree.
    assert train_rows[-1][-1] != test_rows[-1][-1]

    client.delete(f"/api/v1/report/{train_id}")
    client.delete(f"/api/v1/report/{test_id}")


def test_an_incompatible_report_fails_with_its_own_message(
    client: TestClient, trained_run_id: int
):
    """A regression report over a classifier must not produce a plot."""
    report_id = _create(client, trained_run_id, "ResidualPlot")

    with pytest.raises(JobError, match="Failed to compute the report"):
        ReportJob(report_id=report_id).run()

    with client.app.container["session_factory"]() as db:
        assert db.get(Report, report_id).status == ReportStatus.ERROR

    client.delete(f"/api/v1/report/{report_id}")


def test_invalid_split_is_rejected(client: TestClient, trained_run_id: int):
    response = client.post(
        "/api/v1/report/",
        json={
            "run_id": trained_run_id,
            "report_name": "ConfusionMatrix",
            "parameters": {},
            "split": "holdout",
        },
    )
    assert response.status_code == 422


def test_creating_for_an_unknown_run_is_404(client: TestClient):
    response = client.post(
        "/api/v1/report/",
        json={
            "run_id": 99999,
            "report_name": "ConfusionMatrix",
            "parameters": {},
            "split": "test",
        },
    )
    assert response.status_code == 404


def test_retraining_deletes_the_reports(client: TestClient, trained_run_id: int):
    """Reports describe the predictions of the fit being replaced."""
    report_id = _create(client, trained_run_id, "ConfusionMatrix")
    ReportJob(report_id=report_id).run()

    counts = client.get(f"/api/v1/run/{trained_run_id}/operations/count").json()
    assert counts["reports"] == 1

    response = client.delete(f"/api/v1/run/{trained_run_id}/operations")
    assert response.status_code in (200, 204), response.text

    remaining = client.get(f"/api/v1/report/?run_id={trained_run_id}").json()
    assert remaining == []
