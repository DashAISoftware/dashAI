"""What a run that read exogenous variables takes to predict.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.job.base_job import JobError
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.test_forecasting_exogenous_acceptance import (
    ARIMA_PARAMS,
    PROMO,
    _body,
    _frame,
    _future,
    _train,
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


def test_a_dataset_of_future_rows_takes_no_horizon_apart(
    client, tmp_path, exogenous_run
):
    dataset_id = _upload(client, _future(), tmp_path, "with-horizon")
    response = client.post(
        "/api/v1/predict/",
        json={"run_id": exogenous_run, "dataset_id": dataset_id, "horizon": 3},
    )

    assert response.status_code == 422, response.text
    assert "read exogenous variables" in response.json()["detail"]


def test_rows_typed_in_say_how_many_they_are(client, exogenous_run):
    response = client.post("/api/v1/predict/", json={"run_id": exogenous_run})

    assert response.status_code == 422, response.text
    assert "how many rows" in response.json()["detail"]


def test_rows_typed_in_past_the_horizon_measured_are_warned_about(
    client, exogenous_run
):
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "horizon": 5}
    )

    assert response.status_code == 200, response.text
    assert response.json()["unevaluated_steps"] == 2
    assert response.json()["evaluated_horizon"] == 3


def test_the_rows_typed_in_are_as_many_as_were_asked_for(client, exogenous_run):
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "horizon": 3}
    )
    assert response.status_code == 200, response.text
    rows = [
        {"date": "2024-01-01", "promo": 1.0},
        {"date": "2024-02-01", "promo": 0.0},
    ]

    with pytest.raises(JobError, match="3 rows.*2 were typed in"):
        PredictJob(prediction_id=response.json()["id"], manual_input_data=rows).run()


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


def test_the_next_dates_come_in_the_format_the_series_was_given_in(client, tmp_path):
    """A series dated day first is offered its next dates day first, and those
    dates, typed back in, are the ones the run forecasts."""
    from DashAI.back.core.enums.status import PredictionStatus
    from DashAI.back.dependencies.database.models import Prediction

    frame = _frame()
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%d/%m/%Y")
    dataset_id = _upload(
        client,
        frame,
        tmp_path,
        "day-first",
        types={"date": {"type": "Date", "dtype": "%d/%m/%Y"}},
    )
    response = client.post(
        "/api/v1/model-session/", json=_body(dataset_id, exogenous=PROMO)
    )
    assert response.status_code == 201, response.text
    run_id = _train(client, response.json()["id"], "ARIMA", ARIMA_PARAMS)

    response = client.get(
        f"/api/v1/predict/future-dates/{run_id}", params={"horizon": 2}
    )

    assert response.status_code == 200, response.text
    dates = response.json()["dates"]
    assert dates == ["01/01/2024", "01/02/2024"]

    response = client.post("/api/v1/predict/", json={"run_id": run_id, "horizon": 2})
    assert response.status_code == 200, response.text
    rows = [{"date": date, "promo": 0.0} for date in dates]
    PredictJob(prediction_id=response.json()["id"], manual_input_data=rows).run()
    with client.app.container["session_factory"]() as db:
        prediction = db.get(Prediction, response.json()["id"])
        assert prediction.status == PredictionStatus.FINISHED


def test_a_run_whose_training_dataset_was_deleted_is_gone_with_it(
    client, exogenous_run
):
    """Deleting a dataset takes its sessions and their runs with it, so the
    next dates of a run never meet a missing training dataset."""
    from DashAI.back.dependencies.database.models import ModelSession, Run

    with client.app.container["session_factory"]() as db:
        run = db.get(Run, exogenous_run)
        dataset_id = db.get(ModelSession, run.model_session_id).dataset_id

    assert client.delete(f"/api/v1/dataset/{dataset_id}").status_code == 204

    response = client.get(
        f"/api/v1/predict/future-dates/{exogenous_run}", params={"horizon": 2}
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Run not found"
