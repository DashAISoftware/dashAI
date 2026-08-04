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
from DashAI.back.job.explainer_job import ExplainerJob
from DashAI.back.job.explainer_story_job import ExplainerStoryJob
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


@pytest.fixture(scope="module", name="dataset_id")
def dataset_id(dataset_1: Dataset) -> int:
    return dataset_1.id


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


class StoryableGlobalExplainer(BaseGlobalExplainer):
    """Global explainer with a deterministic, testable story()."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def explain(self, dataset):
        return {"headline": "feature X matters most"}

    def plot(self, explanation):
        return [TextArtifact(payload="a plot summary")]

    def story(self, explainer_output):
        headline = (self.explanation or {}).get("headline", "unknown")
        return f"Story based on '{explainer_output.payload}': {headline}"


class StorylessGlobalExplainer(BaseGlobalExplainer):
    """Global explainer that never defines story() at all."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def explain(self, dataset):
        return {"headline": "irrelevant"}

    def plot(self, explanation):
        return [TextArtifact(payload="a plot summary")]


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            DummyTask,
            DummyModel,
            StoryableGlobalExplainer,
            StorylessGlobalExplainer,
            ExplainerJob,
            ExplainerStoryJob,
        ]
    )

    monkeypatch.setitem(
        container._services,
        "component_registry",
        test_registry,
    )
    return test_registry


@pytest.fixture(scope="module", name="model_session_id")
def create_model_session(client: TestClient, dataset_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_id,
            name="DummyExperiment",
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


@pytest.fixture(scope="module", name="global_explainer_id")
def create_global_explainer(client: TestClient, run_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        global_explainer = GlobalExplainer(
            name="test_story_global",
            run_id=run_id,
            explainer_name="StoryableGlobalExplainer",
            parameters={},
        )
        db.add(global_explainer)
        db.commit()
        db.refresh(global_explainer)

        yield global_explainer.id

        db.delete(global_explainer)
        db.commit()
        db.close()


def test_global_story_job(client: TestClient, global_explainer_id: int):
    # First compute the explanation itself, same as any other explainer job.
    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "ExplainerJob",
            "kwargs": json.dumps(
                {
                    "explainer_id": global_explainer_id,
                    "explainer_scope": "global",
                }
            ),
        },
    )
    assert response.status_code == 201, response.text

    response = client.get(f"/api/v1/explainer/global/?run_id={global_explainer_id}")
    # Sanity: the explanation finished (plot_path set) before generating a story.
    explainers = response.json()
    assert explainers[0]["plot_path"], explainers

    # Now request the story for the already-computed explanation, through the
    # dedicated endpoint (not the generic /job/ POST).
    response = client.post(
        f"/api/v1/explainer/global/{global_explainer_id}/story",
    )
    assert response.status_code == 201, response.text
    story_job_id = response.json()["id"]

    response = client.get(f"/api/v1/job/status/{story_job_id}")
    assert response.status_code == 200, response.text
    job_status = response.json()
    assert job_status["status"] == "finished", job_status

    container = client.app.container
    session_factory = container["session_factory"]
    with session_factory() as db:
        explainer = db.get(GlobalExplainer, global_explainer_id)
        assert explainer.story_huey_id == story_job_id
        assert explainer.story == (
            "Story based on 'a plot summary': feature X matters most"
        )


def test_global_story_endpoint_requires_finished_explanation(
    client: TestClient, run_id: int
):
    # A fresh explainer that was never run still has status NOT_STARTED.
    container = client.app.container
    session_factory = container["session_factory"]
    with session_factory() as db:
        unstarted_explainer = GlobalExplainer(
            run_id=run_id,
            explainer_name="StoryableGlobalExplainer",
            parameters={},
        )
        db.add(unstarted_explainer)
        db.commit()
        db.refresh(unstarted_explainer)
        unstarted_id = unstarted_explainer.id

    response = client.post(f"/api/v1/explainer/global/{unstarted_id}/story")
    assert response.status_code == 404, response.text


def test_global_story_endpoint_requires_existing_explainer(client: TestClient):
    response = client.post("/api/v1/explainer/global/999999/story")
    assert response.status_code == 404, response.text


def test_global_story_endpoint_rejects_explainer_without_story(
    client: TestClient, run_id: int
):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        storyless_explainer = GlobalExplainer(
            run_id=run_id,
            explainer_name="StorylessGlobalExplainer",
            parameters={},
        )
        db.add(storyless_explainer)
        db.commit()
        db.refresh(storyless_explainer)
        storyless_id = storyless_explainer.id

    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "ExplainerJob",
            "kwargs": json.dumps(
                {
                    "explainer_id": storyless_id,
                    "explainer_scope": "global",
                }
            ),
        },
    )
    assert response.status_code == 201, response.text

    response = client.post(f"/api/v1/explainer/global/{storyless_id}/story")
    assert response.status_code == 400, response.text
