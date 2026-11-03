"""What a run that read exogenous variables takes to predict.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import numpy as np
import pytest

from DashAI.back.job.base_job import JobError
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.test_forecasting_exogenous_acceptance import (
    _future,
    _upload,
    fixture_exogenous_run,  # noqa: F401
)


def test_it_offers_the_datasets_that_bring_the_dates_and_what_it_read(
    client, tmp_path, exogenous_run
):
    future = _upload(client, _future(), tmp_path, "offered")
    without_promo = _upload(client, _future()[["date"]], tmp_path, "not-offered")

    response = client.get(
        "/api/v1/predict/filter_datasets", params={"run_id": exogenous_run}
    )

    assert response.status_code == 200, response.text
    offered = response.json()["valid_dataset_ids"]
    # The future has no series, and is offered all the same.
    assert future in offered
    assert without_promo not in offered


def test_it_takes_no_horizon_apart_from_the_rows(client, exogenous_run):
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "horizon": 3}
    )

    assert response.status_code == 422, response.text
    assert "read exogenous variables" in response.json()["detail"]


def _predict(client, exogenous_run, dataset_id):
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "dataset_id": dataset_id}
    )
    assert response.status_code == 200, response.text
    PredictJob(prediction_id=response.json()["id"]).run()


def test_a_future_column_of_another_type_is_refused_naming_it(
    client, tmp_path, exogenous_run
):
    future = _future()
    future["promo"] = ["none", "promo", "none", "none"]
    dataset_id = _upload(
        client,
        future,
        tmp_path,
        "text-promo",
        types={"promo": {"type": "Text", "dtype": "string"}},
    )

    with pytest.raises(JobError, match=r"'promo'.*Text.*Float"):
        _predict(client, exogenous_run, dataset_id)


def test_a_future_value_that_is_not_finite_names_the_column_and_the_date(
    client, tmp_path, exogenous_run
):
    future = _future()
    future.loc[1, "promo"] = np.inf
    dataset_id = _upload(client, future, tmp_path, "inf-promo")

    with pytest.raises(JobError, match=r"'promo'.*2024-02-01"):
        _predict(client, exogenous_run, dataset_id)
