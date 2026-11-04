"""Regression net for predicting with an x/y session that preprocesses.

Written before the exogenous PR (RECONCILING_FORECASTING §7) and recorded on
its base, develop ``182120b0a``, with ``DASHAI_RECORD_PREDICT_PREPROCESSING_NET=1``.
That PR teaches ``POST /predict/``, ``filter_datasets`` and ``PredictJob`` a
horizon prediction with future exogenous rows, through the same
``ApplySessionPreprocessingUnit``. An x/y prediction must not notice, and
this pins it on the holdout session of ``test_session_preprocessing_net.py``:

- a prediction on another dataset, with a category training never saw, saved
  and with its ``unseen_categories``;
- a prediction on a partition;
- a manual prediction, through the job and through the preview;
- which datasets ``filter_datasets`` offers, and what ``/predict/splits``
  declares.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from DashAI.back.core.enums.status import PredictionStatus
from DashAI.back.dependencies.database.models import Prediction
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.golden_net import Golden
from tests.back.api.test_column_roles_net import _saved_dataset
from tests.back.api.test_forecasting_acceptance import _get
from tests.back.api.test_session_preprocessing_net import (
    create_session,
    frame,
    train,
    upload,
)

GOLDEN = Golden(
    Path(__file__).with_name("predict_preprocessing_net_golden.json"),
    "DASHAI_RECORD_PREDICT_PREPROCESSING_NET",
)

#: Rows typed by hand carry the raw features the chain scopes on.
MANUAL_ROWS = [
    {"num_a": 12.5, "num_b": 99.0, "color": "red", "day": "2021-12-01"},
    {"num_a": 40.0, "num_b": 104.5, "color": "blue", "day": "2022-01-15"},
]


def _future() -> pd.DataFrame:
    rows = frame().drop(columns=["y", "label"]).head(6).copy()
    rows.loc[2, "color"] = "violet"
    return rows


@pytest.fixture(scope="module", autouse=True)
def _save_golden():
    yield
    GOLDEN.save()


@pytest.fixture(scope="module", name="fitted")
def fixture_fitted(client, tmp_path_factory):
    directory = tmp_path_factory.mktemp("predict-preprocessing-net")
    dataset_id = upload(client, directory, "pred-net-train", frame())
    other_id = upload(client, directory, "pred-net-future", _future())
    without_color = upload(
        client, directory, "pred-net-no-color", _future().drop(columns=["color"])
    )
    session_id = create_session(client, dataset_id, "holdout")
    return {
        "run_id": train(client, session_id),
        "dataset_id": dataset_id,
        "other_id": other_id,
        "without_color": without_color,
    }


def _predict(client, run_id, dataset_id=None, split=None, manual=None) -> dict:
    response = client.post(
        "/api/v1/predict/",
        json={"run_id": run_id, "dataset_id": dataset_id, "split": split},
    )
    assert response.status_code == 200, response.text
    prediction_id = response.json()["id"]
    if manual is None:
        PredictJob(prediction_id=prediction_id).run()
    else:
        PredictJob(prediction_id=prediction_id, manual_input_data=manual).run()
    prediction = _get(client, Prediction, prediction_id)
    assert prediction.status == PredictionStatus.FINISHED
    return {
        "saved": _saved_dataset(prediction.results_path),
        "unseen_categories": prediction.unseen_categories,
    }


def test_a_prediction_on_another_dataset_saves_the_same(client, fitted):
    GOLDEN.pin(
        "dataset", _predict(client, fitted["run_id"], dataset_id=fitted["other_id"])
    )


def test_a_prediction_on_a_partition_saves_the_same(client, fitted):
    GOLDEN.pin(
        "partition",
        _predict(
            client, fitted["run_id"], dataset_id=fitted["dataset_id"], split="test"
        ),
    )


def test_a_manual_prediction_through_the_job_saves_the_same(client, fitted):
    GOLDEN.pin("manual_job", _predict(client, fitted["run_id"], manual=MANUAL_ROWS))


def test_the_manual_preview_answers_the_same(client, fitted):
    response = client.post(
        "/api/v1/predict/preview",
        data={
            "run_id": str(fitted["run_id"]),
            "manual_input_data": json.dumps(MANUAL_ROWS),
        },
    )

    assert response.status_code == 200, response.text
    GOLDEN.pin("manual_preview", response.json())


def test_the_datasets_offered_for_prediction_are_the_same(client, fitted):
    response = client.get(
        "/api/v1/predict/filter_datasets", params={"run_id": fitted["run_id"]}
    )

    assert response.status_code == 200, response.text
    # Ids depend on test order, so they are pinned by which dataset they are.
    names = {
        fitted["dataset_id"]: "train",
        fitted["other_id"]: "future",
        fitted["without_color"]: "without_color",
    }
    ids = response.json()["valid_dataset_ids"]
    GOLDEN.pin("filter_datasets", sorted(names[i] for i in ids if i in names))


def test_the_prediction_declaration_is_the_same(client, fitted):
    response = client.get(f"/api/v1/predict/splits/{fitted['run_id']}")

    assert response.status_code == 200, response.text
    declared = response.json()
    assert declared.pop("training_dataset_id") == fitted["dataset_id"]
    GOLDEN.pin("predict_splits", declared)
