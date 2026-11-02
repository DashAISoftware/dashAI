"""A prediction records the categories its rows had that training never saw.

The encoders treat an unseen category instead of failing (a session's one-hot
by default, a model's own encoders always), and the prediction says so: the
saved prediction keeps one record per encoder and column, and the preview
returns them next to its rows. Nothing is recorded when every category was
seen, and the preview then answers exactly as before.

Hand-typed rows only take categories of the training dataset, so the preview
is tried with one that the dataset has in a single row, outside the training
partition.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import PredictionStatus, RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import Dataset, Prediction, Run
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.predict_job import PredictJob

SCHEMA = {
    "color": {"type": "Categorical", "dtype": "string"},
    "size": {"type": "Float", "dtype": "float64"},
    "label": {"type": "Categorical", "dtype": "string"},
}
COLORS = ["red", "green", "blue"]
#: Only in the last row of the training dataset, which the split leaves out
#: of the training partition.
RARE = "violet"
#: Enough rows for the loader to infer ``color`` as categorical: it reads no
#: schema (``DatasetJob`` ignores ``params["schema"]``).
TRAIN_ROWS = 90
#: By index, so the partition the rare category falls in is known.
HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "train": list(range(60)),
    "validation": list(range(60, 75)),
    "test": list(range(75, 91)),
}


def _frame(colors):
    return pd.DataFrame(
        {
            "color": colors,
            "size": [float(i % 7) for i in range(len(colors))],
            "label": ["yes" if i % 3 else "no" for i in range(len(colors))],
        }
    )


def _create_dataset(client, tmp_path, name, frame) -> int:
    path = Path(tmp_path) / f"{name}.csv"
    frame.to_csv(path, index=False)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        entry = Dataset(name=name, file_path="")
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
                    "name": name,
                    "schema": SCHEMA,
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _get(client, model, row_id):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        row = db.get(model, row_id)
        db.expunge(row)
        return row


def _train(client, dataset_id, name, features, preprocessing):
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "name": name,
            "column_roles": {
                "features": features,
                "target": [{"kind": "raw", "name": "label"}],
            },
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(HOLDOUT),
            "preprocessing": preprocessing,
        },
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": response.json()["id"],
            "model_name": "RandomForestClassifier",
            "name": f"forest of {name}",
            "parameters": {"random_state": 0},
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
    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    return run_id


@pytest.fixture(scope="module", name="datasets")
def fixture_datasets(client: TestClient, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("unseen")
    return {
        "train": _create_dataset(
            client,
            tmp_path,
            "unseen-train",
            _frame([COLORS[i % 3] for i in range(TRAIN_ROWS)] + [RARE]),
        ),
        "new": _create_dataset(
            client,
            tmp_path,
            "unseen-new",
            _frame(["red", "purple", "green", "teal", "purple", "blue"] * 15),
        ),
    }


@pytest.fixture(scope="module", name="runs")
def fixture_runs(client: TestClient, datasets):
    one_hot = [
        {
            "converter": "OneHotEncoder",
            "params": {},
            "scope": [{"kind": "raw", "name": "color"}],
        }
    ]
    return {
        "session": _train(
            client,
            datasets["train"],
            "unseen-session-encoder",
            [{"kind": "group", "step": 0}, {"kind": "raw", "name": "size"}],
            one_hot,
        ),
        "model": _train(
            client,
            datasets["train"],
            "unseen-model-encoder",
            [{"kind": "raw", "name": "color"}, {"kind": "raw", "name": "size"}],
            [],
        ),
    }


def _predict(client, run_id, dataset_id, split=None):
    response = client.post(
        "/api/v1/predict/",
        json={"run_id": run_id, "dataset_id": dataset_id, "split": split},
    )
    assert response.status_code == 200, response.text
    prediction_id = response.json()["id"]
    PredictJob(prediction_id=prediction_id).run()
    prediction = _get(client, Prediction, prediction_id)
    assert prediction.status == PredictionStatus.FINISHED
    return prediction


def _preview(client, run_id, colors):
    response = client.post(
        "/api/v1/predict/preview",
        data={
            "run_id": str(run_id),
            "manual_input_data": json.dumps(
                [{"color": color, "size": 1.0} for color in colors]
            ),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


EXPECTED_SOURCE = {
    "session": "OneHotEncoder (step 1)",
    "model": "RandomForestClassifier (model)",
}


@pytest.mark.parametrize("encoder", sorted(EXPECTED_SOURCE))
def test_a_prediction_records_the_categories_training_never_saw(
    client, datasets, runs, encoder
):
    prediction = _predict(client, runs[encoder], datasets["new"])

    assert prediction.unseen_categories == [
        {
            "source": EXPECTED_SOURCE[encoder],
            "column": "color",
            "values": ["purple", "teal"],
            "count": 2,
        }
    ]
    listed = client.get(f"/api/v1/predict/?prediction_id={prediction.id}").json()
    assert listed[0]["unseen_categories"] == prediction.unseen_categories


@pytest.mark.parametrize("encoder", sorted(EXPECTED_SOURCE))
def test_a_prediction_with_every_category_seen_records_nothing(
    client, datasets, runs, encoder
):
    prediction = _predict(client, runs[encoder], datasets["train"], split="train")

    assert prediction.unseen_categories == []


def test_the_rare_category_is_outside_the_training_partition(client, runs):
    indexes = json.loads(_get(client, Run, runs["session"]).split_indexes)

    assert TRAIN_ROWS not in indexes["train_indexes"]


def test_the_preview_returns_the_unseen_categories_with_its_rows(client, runs):
    preview = _preview(client, runs["session"], ["red", RARE])

    assert len(preview["rows"]) == 2
    assert preview["unseen_categories"] == [
        {
            "source": "OneHotEncoder (step 1)",
            "column": "color",
            "values": [RARE],
            "count": 1,
        }
    ]


def test_a_preview_with_every_category_seen_answers_as_before(client, runs):
    preview = _preview(client, runs["session"], ["red", "blue"])

    assert set(preview) == {"columns", "rows"}


def test_a_manual_prediction_keeps_the_type_of_the_column_the_encoder_read(
    client, runs
):
    """The session's model reads the one-hot columns, not ``color``; the
    saved rows are the raw ones, so ``color`` keeps its training type."""
    response = client.post(
        "/api/v1/predict/", json={"run_id": runs["session"], "dataset_id": None}
    )
    assert response.status_code == 200, response.text
    prediction_id = response.json()["id"]
    PredictJob(
        prediction_id=prediction_id,
        manual_input_data=[{"color": "red", "size": 1.0}],
    ).run()
    prediction = _get(client, Prediction, prediction_id)
    assert prediction.status == PredictionStatus.FINISHED

    saved = load_dataset(str(Path(prediction.results_path) / "dataset"))
    schema = json.loads(saved.arrow_table.schema.metadata[b"dashai_types"])
    assert schema["color"]["type"] == "Categorical"
