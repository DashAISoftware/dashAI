import json

import joblib
import pytest
from datasets import ClassLabel, Value
from fastapi.testclient import TestClient

from DashAI.back.core.artifacts import ArtifactGroup, GroupedArtifacts, TextArtifact
from DashAI.back.dependencies.database.models import (
    Dataset,
    GlobalExplainer,
    LocalExplainer,
    ModelSession,
    Run,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.explainability.local_explainer import BaseLocalExplainer
from DashAI.back.job.explainer_job import ExplainerJob
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
        self.explanation = {"headline": "feature X matters most"}
        return self.explanation

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


class BrokenStoryGlobalExplainer(BaseGlobalExplainer):
    """Global explainer whose story() always raises.

    Used to prove a story bug never fails the explanation itself.
    """

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

    def story(self, explainer_output):
        raise RuntimeError("boom")


class StoryableLocalExplainer(BaseLocalExplainer):
    """Local explainer with a deterministic, testable story() per instance."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def fit(self, dataset, **kwargs):
        return self

    def explain_instance(self, instances):
        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        return {"n_instances": to_dashai_dataset(instances).num_rows}

    def plot(self, explanation):
        groups = [
            ArtifactGroup(
                title=f"Instance {i}", artifacts=[TextArtifact(payload=f"plot {i}")]
            )
            for i in range(explanation["n_instances"])
        ]
        return [GroupedArtifacts(groups=groups)]

    def story(self, explainer_output, prediction_context):
        group = explainer_output.groups[0]
        text = group.artifacts[0].payload
        return f"Local story for '{text}', context rows={prediction_context.num_rows}"


class StorylessLocalExplainer(BaseLocalExplainer):
    """Local explainer that never defines story() at all."""

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def fit(self, dataset, **kwargs):
        return self

    def explain_instance(self, instances):
        return {}

    def plot(self, explanation):
        return [TextArtifact(payload="a plot summary")]


class BrokenStoryLocalExplainer(BaseLocalExplainer):
    """Local explainer whose story() always raises for every instance.

    Used to prove a story bug never fails the explanation itself, and does
    not block other instances (there are none left to block here, but the
    explanation must still finish successfully with stories left empty).
    """

    COMPATIBLE_COMPONENTS = ["DummyTask"]

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.explanation = None

    @classmethod
    def get_schema(cls):
        return {}

    def fit(self, dataset, **kwargs):
        return self

    def explain_instance(self, instances):
        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        return {"n_instances": to_dashai_dataset(instances).num_rows}

    def plot(self, explanation):
        groups = [
            ArtifactGroup(
                title=f"Instance {i}", artifacts=[TextArtifact(payload=f"plot {i}")]
            )
            for i in range(explanation["n_instances"])
        ]
        return [GroupedArtifacts(groups=groups)]

    def story(self, explainer_output, prediction_context):
        raise RuntimeError("boom")


@pytest.fixture(autouse=True, name="test_registry")
def setup_test_registry(client, monkeypatch: pytest.MonkeyPatch):
    container = client.app.container

    test_registry = ComponentRegistry(
        initial_components=[
            DummyTask,
            DummyModel,
            StoryableGlobalExplainer,
            StorylessGlobalExplainer,
            BrokenStoryGlobalExplainer,
            StoryableLocalExplainer,
            StorylessLocalExplainer,
            BrokenStoryLocalExplainer,
            ExplainerJob,
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


def _run_explainer_job(client: TestClient, explainer_id: int, scope: str):
    response = client.post(
        "/api/v1/job/",
        data={
            "job_type": "ExplainerJob",
            "kwargs": json.dumps(
                {"explainer_id": explainer_id, "explainer_scope": scope}
            ),
        },
    )
    assert response.status_code == 201, response.text


def test_global_explainer_job_generates_story_automatically(
    client: TestClient, run_id: int
):
    # The story is generated as part of the normal explainer job - there is
    # no separate job, endpoint or button to request it.
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = GlobalExplainer(
            run_id=run_id,
            explainer_name="StoryableGlobalExplainer",
            parameters={},
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id

    _run_explainer_job(client, explainer_id, "global")

    with session_factory() as db:
        explainer = db.get(GlobalExplainer, explainer_id)
        assert explainer.plot_path, explainer
        assert explainer.story == (
            "Story based on 'a plot summary': feature X matters most"
        )


def test_global_explainer_job_leaves_story_none_when_unsupported(
    client: TestClient, run_id: int
):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = GlobalExplainer(
            run_id=run_id,
            explainer_name="StorylessGlobalExplainer",
            parameters={},
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id

    _run_explainer_job(client, explainer_id, "global")

    with session_factory() as db:
        explainer = db.get(GlobalExplainer, explainer_id)
        assert explainer.plot_path, explainer
        assert explainer.story is None


def test_global_explainer_job_survives_a_broken_story(client: TestClient, run_id: int):
    # A bug in story() must never fail the explanation itself.
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = GlobalExplainer(
            run_id=run_id,
            explainer_name="BrokenStoryGlobalExplainer",
            parameters={},
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id

    _run_explainer_job(client, explainer_id, "global")

    with session_factory() as db:
        explainer = db.get(GlobalExplainer, explainer_id)
        assert explainer.plot_path, explainer
        assert explainer.story is None
        assert explainer.status.name == "FINISHED"


@pytest.fixture(scope="module", name="local_explainer_id")
def create_local_explainer(client: TestClient, run_id: int, dataset_id: int):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        local_explainer = LocalExplainer(
            name="test_story_local",
            run_id=run_id,
            explainer_name="StoryableLocalExplainer",
            dataset_id=dataset_id,
            scope={"split": "test", "percentage": 100},
            parameters={},
            fit_parameters={},
        )
        db.add(local_explainer)
        db.commit()
        db.refresh(local_explainer)

        yield local_explainer.id

        db.delete(local_explainer)
        db.commit()
        db.close()


def test_local_explainer_job_generates_stories_automatically(
    client: TestClient, local_explainer_id: int
):
    # One story per explained instance, all generated automatically as part
    # of the normal explainer job - no separate job/endpoint/button.
    _run_explainer_job(client, local_explainer_id, "local")

    container = client.app.container
    session_factory = container["session_factory"]
    with session_factory() as db:
        explainer = db.get(LocalExplainer, local_explainer_id)
        assert explainer.plots_path, explainer
        # The "test" split has 4 rows (indexes 5-8) at 100%.
        assert explainer.stories == {
            "0": "Local story for 'plot 0', context rows=1",
            "1": "Local story for 'plot 1', context rows=1",
            "2": "Local story for 'plot 2', context rows=1",
            "3": "Local story for 'plot 3', context rows=1",
        }


def test_local_explainer_job_leaves_stories_none_when_unsupported(
    client: TestClient, run_id: int, dataset_id: int
):
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = LocalExplainer(
            run_id=run_id,
            explainer_name="StorylessLocalExplainer",
            dataset_id=dataset_id,
            scope={"split": "test", "percentage": 100},
            parameters={},
            fit_parameters={},
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id

    _run_explainer_job(client, explainer_id, "local")

    with session_factory() as db:
        explainer = db.get(LocalExplainer, explainer_id)
        assert explainer.plots_path, explainer
        assert explainer.stories is None


def test_local_explainer_job_survives_a_broken_story(
    client: TestClient, run_id: int, dataset_id: int
):
    # A bug in one instance's story() must never fail the explanation.
    container = client.app.container
    session_factory = container["session_factory"]

    with session_factory() as db:
        explainer = LocalExplainer(
            run_id=run_id,
            explainer_name="BrokenStoryLocalExplainer",
            dataset_id=dataset_id,
            scope={"split": "test", "percentage": 100},
            parameters={},
            fit_parameters={},
        )
        db.add(explainer)
        db.commit()
        db.refresh(explainer)
        explainer_id = explainer.id

    _run_explainer_job(client, explainer_id, "local")

    with session_factory() as db:
        explainer = db.get(LocalExplainer, explainer_id)
        assert explainer.plots_path, explainer
        assert explainer.stories is None
        assert explainer.status.name == "FINISHED"
