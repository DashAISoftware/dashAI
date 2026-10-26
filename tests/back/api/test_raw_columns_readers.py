"""The endpoints that check a dataset against a session that preprocesses.

The model of such a session reads columns its converters produce, which no
dataset has: what a dataset needs are the raw columns the fitted
preprocessor reads (``ConverterSequence.raw_columns_read``). Comparing it with
the model's own input columns filtered out every dataset, the one the session
was trained on included, so it could not be predicted on nor explained.

The session here has a single input, the Binarizer output of
``SepalLengthCm``: iris is valid, and iris without that column is not.
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import Dataset
from DashAI.back.job.dataset_job import DatasetJob
from tests.back.api.trained_runs import IRIS_CSV, fit_classifier_behind_preprocessing

SCOPED = "SepalLengthCm"


@pytest.fixture(scope="module", name="run_id")
def fixture_run_id(client: TestClient, dataset_1: Dataset, tmp_path_factory):
    return fit_classifier_behind_preprocessing(
        client, dataset_1, tmp_path_factory.mktemp("model"), "raw-columns-readers"
    )


@pytest.fixture(scope="module", name="without_scope")
def fixture_without_scope(client: TestClient, tmp_path_factory) -> int:
    """Iris without the column the session's Binarizer reads."""
    path = tmp_path_factory.mktemp("iris") / "iris_without_scope.csv"
    pd.read_csv(IRIS_CSV).drop(columns=[SCOPED]).to_csv(path, index=False)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        entry = Dataset(name="iris-without-scope", file_path="")
        db.add(entry)
        db.commit()
        db.refresh(entry)
        DatasetJob(
            job_type="DatasetJob",
            kwargs={
                "dataset_id": entry.id,
                "url": "",
                "params": {
                    "dataloader": "CSVDataLoader",
                    "separator": ",",
                    "name": entry.name,
                },
                "file_path": path,
            },
            db=db,
        ).run()
        return entry.id


def test_predicting_offers_the_dataset_the_session_was_trained_on(
    client, run_id, dataset_1, without_scope
):
    response = client.get(f"/api/v1/predict/filter_datasets?run_id={run_id}")

    assert response.status_code == 200, response.text
    valid = response.json()["valid_dataset_ids"]
    assert dataset_1.id in valid
    assert without_scope not in valid


def test_explaining_offers_the_dataset_the_session_was_trained_on(
    client, run_id, dataset_1, without_scope
):
    response = client.post(
        "/api/v1/explainer/local/valid-datasets", json={"run_id": run_id}
    )

    assert response.status_code == 200, response.text
    valid = response.json()["valid_dataset_ids"]
    assert dataset_1.id in valid
    assert without_scope not in valid


def test_the_dataset_the_session_was_trained_on_is_valid_to_explain(
    client, run_id, dataset_1
):
    response = client.post(
        "/api/v1/explainer/local/validate-dataset",
        json={"run_id": run_id, "dataset_id": dataset_1.id},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"dataset_status": "valid"}


def test_a_dataset_without_a_column_the_preprocessing_reads_is_not(
    client, run_id, without_scope
):
    response = client.post(
        "/api/v1/explainer/local/validate-dataset",
        json={"run_id": run_id, "dataset_id": without_scope},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "dataset_status": "invalid",
        "missing_columns": [SCOPED],
    }
