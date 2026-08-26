import json

from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset, ModelSession
from DashAI.back.job.dataset_split_utils import load_dataset_and_splitter

HOLDOUT_SPLITS = {
    "train": 0.6,
    "test": 0.2,
    "validation": 0.2,
    "is_random": True,
    "has_changed": True,
    "seed": 42,
    "shuffle": True,
    "stratify": False,
    "splitType": "random",
    "splitter_name": "HoldoutSplitter",
}


def test_load_dataset_and_splitter_without_output_columns_treats_whole_dataset_as_x(
    client: TestClient, dataset_1: Dataset
) -> None:
    session_factory = client.app.container["session_factory"]
    component_registry = client.app.container["component_registry"]

    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_1.id,
            name="No Columns Split Test",
            task_name="TabularClassificationTask",
            input_columns=[],
            output_columns=[],
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits=json.dumps(HOLDOUT_SPLITS),
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)

        X, Y, splitter, _task, _prepared = load_dataset_and_splitter(
            model_session, db, component_registry
        )

        assert set(X.column_names) == {
            "SepalLengthCm",
            "SepalWidthCm",
            "PetalLengthCm",
            "PetalWidthCm",
            "Species",
        }
        # Y can't truly have 0 columns and still report the right row count
        # (a `datasets.Dataset` quirk: a 0-column Dataset always reports 0
        # rows) — it carries a reserved placeholder column instead.
        assert Y.column_names == ["__no_output_placeholder__"]
        assert len(Y) == len(X)

        x, _y, _splits = splitter.split(X, Y)
        assert len(x["train"]) + len(x["test"]) + len(x["validation"]) == len(X)

        db.delete(model_session)
        db.commit()
