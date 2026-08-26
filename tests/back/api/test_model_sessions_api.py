from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset, ModelSession

INPUT_COLUMNS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
OUTPUT_COLUMNS = ["Species"]

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


def test_model_session_can_be_created_without_columns(
    client: TestClient, dataset_1: Dataset
) -> None:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_1.id,
            name="No Columns Yet",
            task_name="TabularClassificationTask",
            input_columns=None,
            output_columns=None,
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy="HoldoutEvaluationStrategy",
            splits="{}",
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)
        assert model_session.input_columns is None
        assert model_session.output_columns is None
        db.delete(model_session)
        db.commit()
