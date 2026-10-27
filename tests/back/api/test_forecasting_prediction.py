"""A forecasting run predicts by horizon: steps past the end of its series.

The task declares ``PREDICTION_MODE = "horizon"``. A prediction names how many
steps to forecast and no rows: the kept model was fitted on the whole series
and carries its grid, so the dates follow its last one (D6).

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.enums.status import PredictionStatus
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import Dataset, Prediction, Run
from DashAI.back.job.base_job import JobError
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.test_forecasting_acceptance import (
    _get,
    _session_body,
    _train,
)

HORIZON = 4


def _integer_series(directory: Path, client) -> int:
    """A monthly series of whole numbers, as counts are."""
    dates = pd.date_range("2021-01-01", periods=36, freq="MS")
    frame = pd.DataFrame(
        {
            "date": dates.strftime("%d/%m/%Y"),
            "sales": [int(100 + 2 * i + 10 * np.sin(i / 2)) for i in range(36)],
        }
    )
    path = directory / "integer-series.csv"
    frame.to_csv(path, index=False)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        entry = Dataset(name="integer-series", file_path="")
        db.add(entry)
        db.commit()
        db.refresh(entry)
        DatasetJob(
            job_type="DatasetJob",
            kwargs={
                "dataset_id": entry.id,
                "url": "",
                "params": {
                    "name": "integer-series",
                    "dataloader": "CSVDataLoader",
                    "separator": ",",
                    "inferred_types": {
                        "date": {"type": "Date", "dtype": "%d/%m/%Y"},
                        "sales": {"type": "Integer", "dtype": "int64"},
                    },
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


@pytest.fixture(scope="module", name="trained")
def a_trained_forecaster(client, tmp_path_factory):
    directory = tmp_path_factory.mktemp("forecasting-prediction")
    dataset_id = _integer_series(directory, client)
    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(
            dataset_id,
            strategy="ForecastingHoldoutEvaluationStrategy",
            splits={"splitter_name": "TemporalHoldoutSplitter", "horizon": 3},
        ),
    )
    assert response.status_code == 201, response.text
    run_id = _train(client, response.json()["id"], "ARIMA")
    return {"run_id": run_id, "dataset_id": dataset_id}


def _predict(client, **body):
    return client.post("/api/v1/predict/", json=body)


def test_a_horizon_is_forecast_from_the_last_date_on(client, trained):
    from DashAI.back.models.forecasting.arima import ARIMA

    response = _predict(client, run_id=trained["run_id"], horizon=HORIZON)
    assert response.status_code == 200, response.text
    prediction_id = response.json()["id"]

    PredictJob(prediction_id=prediction_id).run()

    prediction = _get(client, Prediction, prediction_id)
    assert prediction.status == PredictionStatus.FINISHED
    assert prediction.horizon == HORIZON
    saved = load_dataset(str(Path(prediction.results_path) / "dataset"))
    rows = saved.to_pandas()
    # The month after the last one trained on, in the format it was given in.
    assert list(rows["date"]) == [
        "01/01/2024",
        "01/02/2024",
        "01/03/2024",
        "01/04/2024",
    ]
    # The kept model, fitted on the whole series, is what forecasts.
    kept = ARIMA.load(_get(client, Run, trained["run_id"]).run_path)
    assert list(rows["sales"]) == pytest.approx(list(kept.predict(HORIZON).point))


def test_a_forecast_of_a_whole_number_series_is_saved_as_a_float(client, trained):
    # FORECASTING M8: the forecast inherited the series' Integer type and was
    # truncated or refused.
    response = _predict(client, run_id=trained["run_id"], horizon=2)
    PredictJob(prediction_id=response.json()["id"]).run()

    prediction = _get(client, Prediction, response.json()["id"])
    saved = load_dataset(str(Path(prediction.results_path) / "dataset"))
    assert saved.types["sales"].to_string()["type"] == "Float"
    assert any(value != int(value) for value in saved.to_pandas()["sales"])


def test_a_horizon_past_the_evaluated_one_says_how_many_steps_were_not(client, trained):
    response = _predict(client, run_id=trained["run_id"], horizon=5)

    assert response.status_code == 200, response.text
    assert response.json()["unevaluated_steps"] == 2


def test_a_horizon_within_the_evaluated_one_has_no_warning(client, trained):
    response = _predict(client, run_id=trained["run_id"], horizon=3)

    assert "unevaluated_steps" not in response.json()


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ({"horizon": 2, "split": "test"}, "not a dataset nor a partition"),
        ({"horizon": 2, "dataset_id": "train"}, "not a dataset nor a partition"),
        ({}, "give the horizon"),
    ],
    ids=["a partition", "a dataset", "no horizon"],
)
def test_a_forecasting_run_takes_a_horizon_and_no_rows(client, trained, extra, message):
    if extra.get("dataset_id") == "train":
        extra = {**extra, "dataset_id": trained["dataset_id"]}

    response = _predict(client, run_id=trained["run_id"], **extra)

    assert response.status_code == 422, response.text
    assert message in response.text


def test_a_horizon_is_refused_for_a_task_that_predicts_rows(
    client, dataset_1, tmp_path
):
    from tests.back.api.trained_runs import fit_regressor

    run_id = fit_regressor(client, dataset_1, tmp_path, "rows-not-horizon")

    response = _predict(client, run_id=run_id, horizon=3)

    assert response.status_code == 422, response.text
    assert "predicts rows, not a horizon" in response.text


def test_the_job_refuses_rows_for_a_forecasting_run_the_api_would_have_refused(
    client, trained
):
    # A row written without the API: the job is the second line.
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        prediction = Prediction(
            run_id=trained["run_id"], dataset_id=trained["dataset_id"], split="test"
        )
        db.add(prediction)
        db.commit()
        prediction_id = prediction.id

    with pytest.raises(JobError, match="takes a horizon, not rows"):
        PredictJob(prediction_id=prediction_id).run()

    assert _get(client, Prediction, prediction_id).status == PredictionStatus.ERROR
