import json

import joblib
import pytest
from datasets import ClassLabel, Value
from fastapi.testclient import TestClient

from DashAI.back.core.artifacts import TextArtifact
from DashAI.back.dependencies.database.models import (
    Dataset,
    GlobalExplainer,
    ModelSession,
    Run,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.insights.analyzers.explainer_insights import (
    EXPLAINER_INSIGHT_ANALYZERS,
    PartialDependenceInsightAnalyzer,
)
from DashAI.back.job.explainer_job import ExplainerJob
from DashAI.back.job.insight_generation_job import InsightGenerationJob
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.base_model import BaseModel
from DashAI.back.tasks.base_task import BaseTask

input_columns = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
output_columns = ["Species"]
splits = json.dumps(
    {
        "train": 0.5,
        "test": 0.2,
        "validation": 0.3,
        "is_random": True,
        "has_changed": True,
        "seed": 42,
        "shuffle": True,
        "stratify": False,
    }
)

FACTS = {
    "feature": "age",
    "target": "yes",
    "trend": "increases",
    "start_value": 20,
    "end_value": 65,
    "start_pred": 0.1,
    "end_pred": 0.5,
    "min_pred": 0.1,
    "max_pred": 0.5,
}


class DummyTask(BaseTask):
    name: str = "DummyTask"

    metadata: dict = {
        "inputs_types": [ClassLabel, Value],
        "outputs_types": [ClassLabel],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }

    def prepare_for_task(self, dataset, input_columns=None, output_columns=None):
        return dataset


class DummyModel(BaseModel):
    COMPATIBLE_COMPONENTS = ["DummyTask"]

    @classmethod
    def get_schema(cls):
        return {}

    def save(self, filename):
        joblib.dump(self, filename)

    @staticmethod
    def load(filename):
        return DummyModel()

    def predict(self, x):
        return {}

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return

    def prepare_dataset(self, dataset, is_fit=False):
        return dataset

    def prepare_output(self, dataset, is_fit=False):
        return dataset


class DummyGlobalExplainerWithInsights(BaseGlobalExplainer):
    """Global explainer that supports AI insights, for a single artifact."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def explain(self, dataset):
        return {"dummy": True}

    def plot(self, explanation):
        return [TextArtifact(title="Dummy Curve", payload="dummy")]

    def insight_facts(self, explanation, explainer_output):
        if explainer_output.title != "Dummy Curve":
            return None
        return dict(FACTS)


class DummyGlobalExplainerWithoutInsights(BaseGlobalExplainer):
    """Global explainer with no AI insight support (no ``insight_facts``)."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def explain(self, dataset):
        return {"dummy": True}

    def plot(self, explanation):
        return [TextArtifact(title="Dummy Curve", payload="dummy")]


class DummyGenerativeModel(BaseGenerativeModel):
    REQUIRES_DOWNLOAD = False

    def __init__(self, **kwargs):
        pass

    def generate(self, messages):
        return ["a generated insight"]


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    """Setup a test registry with the dummy task/model/explainers/jobs."""
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            DummyTask,
            DummyModel,
            DummyGenerativeModel,
            DummyGlobalExplainerWithInsights,
            DummyGlobalExplainerWithoutInsights,
            ExplainerJob,
            InsightGenerationJob,
        ]
    )

    monkeypatch.setitem(container._services, "component_registry", test_registry)
    monkeypatch.setitem(
        EXPLAINER_INSIGHT_ANALYZERS,
        "DummyGlobalExplainerWithInsights",
        PartialDependenceInsightAnalyzer,
    )
    return test_registry


@pytest.fixture(scope="module", name="dataset_id")
def dataset_id(dataset_1: Dataset) -> int:
    return dataset_1.id


@pytest.fixture(scope="module", name="model_session_id", autouse=True)
def create_model_session(client: TestClient, dataset_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_id,
            name="DummyInsightsExperiment",
            task_name="DummyTask",
            input_columns=input_columns,
            output_columns=output_columns,
            splits=splits,
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)

        yield model_session.id

        db.delete(model_session)
        db.commit()
        db.close()


@pytest.fixture(scope="module", name="run_id")
def create_run_id(client: TestClient, model_session_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        run = Run(
            model_session_id=model_session_id,
            optimizer_name="OptunaOptimizer",
            optimizer_parameters={
                "n_trials": 10,
                "sampler": "TPESampler",
                "pruner": "None",
            },
            model_name="DummyModel",
            parameters={},
            goal_metric="Accuracy",
            name="Run",
            split_indexes="""{
                "train_indexes": [0, 1, 2, 3, 4],
                "test_indexes": [5, 6, 7, 8],
                "val_indexes": [9, 10, 11, 12]
            }""",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        yield run.id

        db.delete(run)
        db.commit()
        db.close()


def _create_finished_global_explainer(
    client: TestClient, run_id: int, explainer_name: str
) -> int:
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = GlobalExplainer(
            run_id=run_id, explainer_name=explainer_name, parameters={}
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
    job_status = client.get(f"/api/v1/job/status/{response.json()['id']}").json()
    assert job_status["status"] == "finished", job_status

    return explainer_id


@pytest.fixture(name="explainer_with_insights_id")
def explainer_with_insights_id(client: TestClient, run_id: int) -> int:
    return _create_finished_global_explainer(
        client, run_id, "DummyGlobalExplainerWithInsights"
    )


@pytest.fixture(name="explainer_without_insights_id")
def explainer_without_insights_id(client: TestClient, run_id: int) -> int:
    return _create_finished_global_explainer(
        client, run_id, "DummyGlobalExplainerWithoutInsights"
    )


def test_create_explainer_insight_generates_the_text_end_to_end(
    client: TestClient, explainer_with_insights_id: int
):
    response = client.post(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}",
        json={
            "artifact_title": "Dummy Curve",
            "provider_kind": "local",
            "provider_params": {"model_name": "DummyGenerativeModel"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()

    job_status = client.get(f"/api/v1/job/status/{body['id']}").json()
    assert job_status["status"] == "finished", job_status

    insight = client.get(f"/api/v1/insight/{body['insight_result_id']}").json()
    assert insight["status"] == "FINISHED"
    assert insight["result_text"] == "a generated insight"
    assert insight["error_message"] is None


def test_create_explainer_insight_404s_for_a_missing_explainer(client: TestClient):
    response = client.post(
        "/api/v1/insight/explainer/global/31415",
        json={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 404


def test_create_explainer_insight_404s_without_an_analyzer(
    client: TestClient, explainer_without_insights_id: int
):
    response = client.post(
        f"/api/v1/insight/explainer/global/{explainer_without_insights_id}",
        json={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 404


def test_create_explainer_insight_404s_for_an_unknown_artifact_title(
    client: TestClient, explainer_with_insights_id: int
):
    response = client.post(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}",
        json={"artifact_title": "Not A Real Title"},
    )
    assert response.status_code == 404


def test_create_explainer_insight_400s_for_an_invalid_scope(
    client: TestClient, explainer_with_insights_id: int
):
    response = client.post(
        f"/api/v1/insight/explainer/bogus/{explainer_with_insights_id}",
        json={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 400


def test_get_insight_404s_for_a_missing_id(client: TestClient):
    response = client.get("/api/v1/insight/31415")
    assert response.status_code == 404


def test_get_latest_explainer_insight_returns_nulls_when_none_exists(
    client: TestClient, explainer_with_insights_id: int
):
    response = client.get(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}/latest",
        params={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "insight_result_id": None,
        "status": None,
        "result_text": None,
        "error_message": None,
        "huey_id": None,
    }


def test_get_latest_explainer_insight_returns_the_generated_text(
    client: TestClient, explainer_with_insights_id: int
):
    create_response = client.post(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}",
        json={
            "artifact_title": "Dummy Curve",
            "provider_kind": "local",
            "provider_params": {"model_name": "DummyGenerativeModel"},
        },
    )
    assert create_response.status_code == 201, create_response.text

    response = client.get(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}/latest",
        params={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FINISHED"
    assert body["result_text"] == "a generated insight"
    assert body["insight_result_id"] == create_response.json()["insight_result_id"]


def test_get_latest_explainer_insight_returns_the_most_recent_of_several(
    client: TestClient, explainer_with_insights_id: int
):
    first = client.post(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}",
        json={
            "artifact_title": "Dummy Curve",
            "provider_kind": "local",
            "provider_params": {"model_name": "DummyGenerativeModel"},
        },
    ).json()
    second = client.post(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}",
        json={
            "artifact_title": "Dummy Curve",
            "provider_kind": "local",
            "provider_params": {"model_name": "DummyGenerativeModel"},
        },
    ).json()
    assert first["insight_result_id"] != second["insight_result_id"]

    response = client.get(
        f"/api/v1/insight/explainer/global/{explainer_with_insights_id}/latest",
        params={"artifact_title": "Dummy Curve"},
    )
    assert response.json()["insight_result_id"] == second["insight_result_id"]


def test_get_latest_explainer_insight_400s_for_an_invalid_scope(
    client: TestClient, explainer_with_insights_id: int
):
    response = client.get(
        f"/api/v1/insight/explainer/bogus/{explainer_with_insights_id}/latest",
        params={"artifact_title": "Dummy Curve"},
    )
    assert response.status_code == 400
