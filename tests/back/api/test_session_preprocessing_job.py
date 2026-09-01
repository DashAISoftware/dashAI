import json
import os

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import SessionPreprocessingStatus
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import Dataset, ModelSession
from DashAI.back.job.base_job import JobError
from DashAI.back.job.session_preprocessing_job import (
    SessionPreprocessingJob,
    load_preprocessed_session_data,
)

INPUT_COLUMNS = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]
OUTPUT_COLUMNS = ["Species"]


@pytest.fixture(scope="module", name="dataset_id")
def dataset_id(dataset_1: Dataset) -> int:
    """Get the dataset ID from the dataset_1 fixture (iris.csv, 150 rows)."""
    return dataset_1.id


def _create_model_session(
    client: TestClient,
    dataset_id: int,
    evaluation_strategy: str,
    splits: dict,
    converters: list,
    name: str,
    input_columns: list = INPUT_COLUMNS,
    output_columns: list = OUTPUT_COLUMNS,
) -> int:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = ModelSession(
            dataset_id=dataset_id,
            name=name,
            task_name="TabularClassificationTask",
            input_columns=input_columns,
            output_columns=output_columns,
            train_metrics=[],
            validation_metrics=[],
            test_metrics=[],
            evaluation_strategy=evaluation_strategy,
            splits=json.dumps(splits),
            converters=converters,
        )
        db.add(model_session)
        db.commit()
        db.refresh(model_session)
        return model_session.id


def _get_session(client: TestClient, model_session_id: int) -> ModelSession:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = db.get(ModelSession, model_session_id)
        db.expunge(model_session)
        return model_session


def _delete_session(client: TestClient, model_session_id: int) -> None:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = db.get(ModelSession, model_session_id)
        if model_session:
            db.delete(model_session)
            db.commit()


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

CV_SPLITS = {
    "train": 0.5,
    "test": 0.2,
    "validation": 0.3,
    "is_random": True,
    "has_changed": True,
    "seed": 42,
    "shuffle": False,
    "stratify": False,
    "splitType": "random",
    "splitter_name": "KFoldSplitter",
    "n_splits": 3,
}

STANDARD_SCALER_CONFIG = [{"converter": "StandardScaler", "params": {}, "columns": []}]


def test_holdout_preprocessing_produces_partitions_and_fitted_converters(
    client: TestClient, dataset_id: int
):
    model_session_id = _create_model_session(
        client,
        dataset_id,
        evaluation_strategy="HoldoutEvaluationStrategy",
        splits=HOLDOUT_SPLITS,
        converters=STANDARD_SCALER_CONFIG,
        name="Holdout Preprocessing Session",
    )

    SessionPreprocessingJob(kwargs={"model_session_id": model_session_id}).run()

    model_session = _get_session(client, model_session_id)
    assert model_session.preprocessing_status == SessionPreprocessingStatus.FINISHED
    assert model_session.preprocessed_path is not None

    session_dir = model_session.preprocessed_path
    total_rows = 0
    for split_name in ("train", "validation", "test"):
        loaded = load_dataset(os.path.join(session_dir, split_name))
        assert set(loaded.column_names) == set(INPUT_COLUMNS + OUTPUT_COLUMNS)
        assert len(loaded) > 0
        total_rows += len(loaded)
    assert total_rows == 150  # iris.csv has 150 rows

    assert os.path.exists(f"{session_dir}_converters.pkl")

    _delete_session(client, model_session_id)


def test_cv_preprocessing_produces_folds_and_full_dataset(
    client: TestClient, dataset_id: int
):
    model_session_id = _create_model_session(
        client,
        dataset_id,
        evaluation_strategy="CrossValidationEvaluationStrategy",
        splits=CV_SPLITS,
        converters=STANDARD_SCALER_CONFIG,
        name="CV Preprocessing Session",
    )

    SessionPreprocessingJob(kwargs={"model_session_id": model_session_id}).run()

    model_session = _get_session(client, model_session_id)
    assert model_session.preprocessing_status == SessionPreprocessingStatus.FINISHED
    session_dir = model_session.preprocessed_path

    fold_totals = []
    for i in range(3):
        fold_train = load_dataset(os.path.join(session_dir, f"fold_{i}", "train"))
        fold_test = load_dataset(os.path.join(session_dir, f"fold_{i}", "test"))
        assert len(fold_train) > 0
        assert len(fold_test) > 0
        fold_totals.append(len(fold_train) + len(fold_test))

    # every fold's train+test covers the whole dataset.
    assert all(total == fold_totals[0] for total in fold_totals)

    full_train = load_dataset(os.path.join(session_dir, "full_dataset", "train"))
    assert len(full_train) == fold_totals[0]
    # the full_dataset fold's test partition is empty, so it's never saved.
    assert not os.path.exists(os.path.join(session_dir, "full_dataset", "test"))

    assert os.path.exists(f"{session_dir}_converters.pkl")

    _delete_session(client, model_session_id)


def test_loading_survives_a_converter_that_renames_input_columns(
    client: TestClient, dataset_id: int
):
    """Regression test: a converter that changes the input columns'
    names/count (e.g. PCA, which replaces the 4 iris columns with N
    components) must load correctly once `model_session.input_columns` is
    updated to the post-conversion names — exactly what the wizard's
    Columns step does (it only ever runs *after* preprocessing, so it never
    sees the pre-conversion names in the first place). Preprocessing itself
    still runs with the original 4 iris columns as input, same as the real
    wizard: converters apply before the Columns step has set anything.

    `_load_partition` selects `input_columns` directly rather than
    inferring "everything except output" — that heuristic used to let a
    converter's leftover original column (e.g. BagOfWords appending
    `bow_<word>` next to the untouched source text) silently leak into
    training data the user never selected."""
    pca_config = [{"converter": "PCA", "params": {"n_components": 2}, "columns": []}]
    model_session_id = _create_model_session(
        client,
        dataset_id,
        evaluation_strategy="HoldoutEvaluationStrategy",
        splits=HOLDOUT_SPLITS,
        converters=pca_config,
        name="PCA Preprocessing Session",
    )

    SessionPreprocessingJob(kwargs={"model_session_id": model_session_id}).run()

    # Simulates the wizard's Columns step: it only runs after preprocessing,
    # and only ever offers the *current* (already-transformed) columns.
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = db.get(ModelSession, model_session_id)
        model_session.input_columns = ["pca0", "pca1"]
        db.commit()

    model_session = _get_session(client, model_session_id)
    assert model_session.preprocessing_status == SessionPreprocessingStatus.FINISHED

    x, y = load_preprocessed_session_data(model_session)
    # PCA replaced the 4 original input columns with 2 components.
    assert set(x["train"].column_names) == {"pca0", "pca1"}
    assert set(y["train"].column_names) == set(OUTPUT_COLUMNS)
    assert len(x["train"]) == len(y["train"])

    _delete_session(client, model_session_id)


def test_loading_excludes_a_converters_leftover_original_column(
    client: TestClient, dataset_id: int
):
    """Regression test: a converter that *appends* a new column instead of
    replacing the original (e.g. `LabelEncoder` leaving `Species` next to
    the `le_Species` it adds, or `BagOfWords` leaving the source text next
    to its `bow_<word>` columns) used to leak that untouched original
    column into training data — `_load_partition` inferred input columns
    as "everything except output", so a column that's neither the selected
    input nor the selected output still slipped through. Here `Species`
    (the label) is neither the chosen input (the 4 numeric columns) nor
    the chosen output (`le_Species`) — it must not appear in `x` at all."""
    label_encoder_config = [
        {"converter": "LabelEncoder", "params": {}, "columns": ["Species"]}
    ]
    model_session_id = _create_model_session(
        client,
        dataset_id,
        evaluation_strategy="HoldoutEvaluationStrategy",
        splits=HOLDOUT_SPLITS,
        converters=label_encoder_config,
        name="LabelEncoder Leftover Column Session",
        # No columns chosen yet — matches the real wizard order (Preprocessing
        # runs before Columns), and gives LabelEncoder access to "Species"
        # within X (it wouldn't be there if output_columns had already split
        # it out into Y before the converter ran).
        input_columns=[],
        output_columns=[],
    )

    SessionPreprocessingJob(kwargs={"model_session_id": model_session_id}).run()

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        model_session = db.get(ModelSession, model_session_id)
        model_session.input_columns = INPUT_COLUMNS
        model_session.output_columns = ["le_Species"]
        db.commit()

    model_session = _get_session(client, model_session_id)
    assert model_session.preprocessing_status == SessionPreprocessingStatus.FINISHED

    x, y = load_preprocessed_session_data(model_session)
    assert set(x["train"].column_names) == set(INPUT_COLUMNS)
    assert "Species" not in x["train"].column_names
    assert set(y["train"].column_names) == {"le_Species"}
    assert len(x["train"]) == len(y["train"])

    _delete_session(client, model_session_id)


def test_preprocessing_fit_failure_sets_error_status(
    client: TestClient, dataset_id: int
):
    # n_components > number of input columns (4): sklearn's PCA.fit raises.
    pca_config = [{"converter": "PCA", "params": {"n_components": 10}, "columns": []}]
    model_session_id = _create_model_session(
        client,
        dataset_id,
        evaluation_strategy="HoldoutEvaluationStrategy",
        splits=HOLDOUT_SPLITS,
        converters=pca_config,
        name="Preprocessing Error Session",
    )

    with pytest.raises(JobError):
        SessionPreprocessingJob(kwargs={"model_session_id": model_session_id}).run()

    model_session = _get_session(client, model_session_id)
    assert model_session.preprocessing_status == SessionPreprocessingStatus.ERROR
    assert model_session.preprocessed_path is None

    _delete_session(client, model_session_id)
