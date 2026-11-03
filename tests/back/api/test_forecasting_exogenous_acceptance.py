"""Acceptance cases for the exogenous variables, written before the PR.

Each case states what the exogenous PR (RECONCILING_FORECASTING §2.14, §7) has
to deliver, decision by decision. Each is a strict ``xfail`` until the slice
that delivers it, made to fail for the reason it names before the fix: an
``ImportError``, or a 422 because the ``exogenous`` role does not exist yet,
does not count. Its marker comes off with the fix.

The series is monthly, 48 steps, and its sales move with a planned promotion,
so a model that reads the promotion forecasts differently from one that does
not.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.enums.status import PredictionStatus, RunStatus
from DashAI.back.dependencies.database.models import (
    Dataset,
    ModelSession,
    Prediction,
    Run,
)
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.job.predict_job import PredictJob
from tests.back.api.test_forecasting_acceptance import (
    CV,
    ROLLING,
    TASK,
    _create_run,
    _get,
)

N_STEPS = 48
HORIZON = 3


def pending(slice_name: str):
    return pytest.mark.xfail(strict=True, reason=f"PR 5, slice {slice_name}")


# --------------------------------------------------------------------------- #
# Series and sessions
# --------------------------------------------------------------------------- #


def _promo(n: int) -> np.ndarray:
    return np.array([1.0 if i % 4 == 1 else 0.0 for i in range(n)])


def _frame(n: int = N_STEPS, *, start: str = "2020-01-01") -> pd.DataFrame:
    steps = np.arange(n)
    promo = _promo(n)
    dates = pd.date_range(start, periods=n, freq="MS")
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "sales": 100.0 + 0.8 * steps + 15.0 * promo + np.cos(steps),
            "promo": promo,
            "holiday": ["yes" if d.month == 12 else "no" for d in dates],
        }
    )


TYPES = {
    "date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "sales": {"type": "Float", "dtype": "float64"},
    "promo": {"type": "Float", "dtype": "float64"},
    "holiday": {"type": "Categorical", "dtype": "string"},
}


def _upload(client, frame: pd.DataFrame, directory: Path, name: str) -> int:
    path = directory / f"{name}.csv"
    frame.to_csv(path, index=False)
    with client.app.container["session_factory"]() as db:
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
                    "name": name,
                    "dataloader": "CSVDataLoader",
                    "separator": ",",
                    "inferred_types": {c: TYPES[c] for c in frame.columns},
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _body(dataset_id: int, exogenous=None, preprocessing=None) -> dict:
    roles = {
        "time_index": [{"kind": "raw", "name": "date"}],
        "series": [{"kind": "raw", "name": "sales"}],
    }
    if exogenous is not None:
        roles["exogenous"] = exogenous
    return {
        "dataset_id": dataset_id,
        "task_name": TASK,
        "name": f"exogenous-{dataset_id}",
        "column_roles": roles,
        "train_metrics": [],
        "validation_metrics": ["MAE"],
        "test_metrics": ["MAE"],
        "evaluation_strategy": CV,
        "splits": json.dumps(ROLLING),
        "preprocessing": preprocessing or [],
    }


PROMO = [{"kind": "raw", "name": "promo"}]
ONE_HOT_HOLIDAY = {
    "converter": "OneHotEncoder",
    "params": {},
    "scope": [{"kind": "raw", "name": "holiday"}],
}


def _session(client, tmp_path, frame=None, **body) -> int:
    dataset_id = _upload(client, _frame() if frame is None else frame, tmp_path, "x")
    response = client.post("/api/v1/model-session/", json=_body(dataset_id, **body))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _train(client, session_id, model, params=None) -> int:
    run_id = _create_run(client, session_id, model, params)
    ModelJob(run_id=run_id).run()
    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    return run_id


def _forecasts(client, run_id) -> dict:
    response = client.get(f"/api/v1/run/{run_id}/forecasts")
    assert response.status_code == 200, response.text
    return response.json()


ARIMA_PARAMS = {"p": 1, "d": 0, "q": 0}


# --------------------------------------------------------------------------- #
# Slice 2: the role and the row rule
# --------------------------------------------------------------------------- #


def test_the_task_declares_an_exogenous_role(client):
    registry = client.app.container["component_registry"]
    roles = {r["name"]: r for r in registry[TASK]["metadata"]["column_roles"]}

    exogenous = roles["exogenous"]
    assert (exogenous["min"], exogenous["max"]) == (0, "n")
    assert exogenous["transformable"] is True
    assert sorted(exogenous["types"]) == ["Float", "Integer"]
    assert registry[TASK]["metadata"]["takes_preprocessing"] is True


def test_a_second_column_feeds_the_exogenous_role_not_another_task():
    from DashAI.back.tasks.single_series_forecasting_task import (
        SingleSeriesForecastingTask,
    )

    task = SingleSeriesForecastingTask()
    io = task.io_columns(
        {"time_index": ["date"], "series": ["sales"], "exogenous": ["promo"]}
    )

    assert io.inputs == ["date", "promo"]
    assert task.roles_from_io(io.inputs, io.outputs) == {
        "time_index": ["date"],
        "exogenous": ["promo"],
        "series": ["sales"],
    }


def test_a_step_that_changes_rows_is_refused_by_a_task_with_a_time_index(
    client, tmp_path
):
    dataset_id = _upload(client, _frame(), tmp_path, "rows")

    response = client.post(
        "/api/v1/model-session/preprocessing/structure",
        json={
            "dataset_id": dataset_id,
            "task_name": TASK,
            "column_roles": {
                "time_index": ["date"],
                "series": ["sales"],
                "exogenous": ["promo"],
            },
            "steps": [
                {"converter": "NanRemover", "params": {}, "scope": PROMO},
            ],
        },
    )

    assert response.status_code == 200, response.text
    errors = [step["error"] for step in response.json()["steps"] if step["error"]]
    assert [e["code"] for e in errors] == ["changes_rows"]


# --------------------------------------------------------------------------- #
# Slice 3: one fit per cut
# --------------------------------------------------------------------------- #


@pending("3")
def test_a_session_preprocesses_its_exogenous_columns_once_per_cut(client, tmp_path):
    session_id = _session(
        client,
        tmp_path,
        exogenous=PROMO + [{"kind": "group", "step": 0}],
        preprocessing=[ONE_HOT_HOLIDAY],
    )

    session = _get(client, ModelSession, session_id)
    assert session.preprocessing_status == "ready"
    assert sorted(Path(session.preprocessing_artifacts_path).iterdir()) == sorted(
        Path(session.preprocessing_artifacts_path) / name
        for name in [
            "origin_0.pkl",
            "origin_1.pkl",
            "origin_2.pkl",
            "test.pkl",
            "final.pkl",
        ]
    )


# --------------------------------------------------------------------------- #
# Slice 4: the unit per cut
# --------------------------------------------------------------------------- #


@pending("4")
def test_a_gap_in_an_exogenous_column_fails_the_run_naming_column_and_date(
    client, tmp_path
):
    from DashAI.back.job.base_job import JobError

    frame = _frame()
    frame.loc[10, "promo"] = np.nan
    session_id = _session(client, tmp_path, frame, exogenous=PROMO)
    run_id = _create_run(client, session_id, "ARIMA", ARIMA_PARAMS)

    with pytest.raises(JobError, match=r"promo.*2020-11-01"):
        ModelJob(run_id=run_id).run()


@pending("4")
def test_an_imputer_in_the_session_fills_a_gap_in_the_history(client, tmp_path):
    frame = _frame()
    frame.loc[10, "promo"] = np.nan
    imputer = {
        "converter": "SimpleImputer",
        "params": {"strategy": "mean"},
        "scope": PROMO,
    }
    session_id = _session(
        client,
        tmp_path,
        frame,
        exogenous=[{"kind": "group", "step": 0}],
        preprocessing=[imputer],
    )

    _train(client, session_id, "ARIMA", ARIMA_PARAMS)


# --------------------------------------------------------------------------- #
# Slice 6: x reaches the model, and the run records it
# --------------------------------------------------------------------------- #


@pending("6")
def test_arima_forecasts_every_origin_with_the_exogenous_columns(client, tmp_path):
    from DashAI.back.models.forecasting.arima import ARIMA

    frame = _frame()
    session_id = _session(client, tmp_path, frame, exogenous=PROMO)
    run_id = _train(client, session_id, "ARIMA", ARIMA_PARAMS)

    sales = frame["sales"].to_numpy()
    promo = frame[["promo"]].to_numpy()
    for record in _forecasts(client, run_id)["origins"]:
        o = record["origin"]
        by_hand = ARIMA(**ARIMA_PARAMS).fit(sales[:o], promo[:o])
        expected = by_hand.predict(HORIZON, x_future=promo[o : o + HORIZON]).point
        assert record["forecast"] == pytest.approx(list(expected), rel=1e-6)


@pending("6")
def test_the_run_records_whether_it_used_the_exogenous_columns(client, tmp_path):
    session_id = _session(client, tmp_path, exogenous=PROMO)

    arima = _get(client, Run, _train(client, session_id, "ARIMA", ARIMA_PARAMS))
    naive = _get(client, Run, _train(client, session_id, "NaiveForecaster"))
    switched_off = _get(
        client,
        Run,
        _train(client, session_id, "ARIMA", {**ARIMA_PARAMS, "use_exogenous": False}),
    )

    columns = [{"name": "promo", "type": "Float"}]
    assert arima.exogenous == {"used": True, "columns": columns, "reason": None}
    assert naive.exogenous["used"] is False
    assert naive.exogenous["reason"]["key"] == "modelTakesNoExogenous"
    assert switched_off.exogenous["used"] is False
    assert switched_off.exogenous["reason"]["key"] == "exogenousSwitchedOff"


@pending("6")
def test_with_the_switch_off_arima_forecasts_as_without_exogenous(client, tmp_path):
    frame = _frame()
    with_role = _session(client, tmp_path / "a", frame, exogenous=PROMO)
    without = _session(client, tmp_path / "b", frame)

    off = _train(client, with_role, "ARIMA", {**ARIMA_PARAMS, "use_exogenous": False})
    plain = _train(client, without, "ARIMA", ARIMA_PARAMS)

    assert _forecasts(client, off)["origins"] == _forecasts(client, plain)["origins"]


@pending("6")
def test_a_session_without_exogenous_records_none(client, tmp_path):
    session_id = _session(client, tmp_path)

    run_id = _train(client, session_id, "ARIMA", ARIMA_PARAMS)

    assert _get(client, Run, run_id).exogenous is None


# --------------------------------------------------------------------------- #
# Slice 7: the mark before training
# --------------------------------------------------------------------------- #


@pending("7")
def test_the_session_declares_which_models_will_use_the_exogenous(client, tmp_path):
    session_id = _session(client, tmp_path, exogenous=PROMO)

    response = client.get(f"/api/v1/model-session/{session_id}/exogenous-use")

    assert response.status_code == 200, response.text
    by_model = {m["model"]: m for m in response.json()["models"]}
    assert by_model["ARIMA"]["uses"] is True
    assert by_model["ARIMA"]["switch"] == "use_exogenous"
    assert by_model["NaiveForecaster"]["uses"] is False
    assert by_model["NaiveForecaster"]["reason"]["key"] == "modelTakesNoExogenous"


# --------------------------------------------------------------------------- #
# Slice 8: predicting with future exogenous values
# --------------------------------------------------------------------------- #


@pytest.fixture(name="exogenous_run")
def fixture_exogenous_run(client, tmp_path):
    session_id = _session(client, tmp_path, exogenous=PROMO)
    return _train(client, session_id, "ARIMA", ARIMA_PARAMS)


def _future(n: int = 4) -> pd.DataFrame:
    """The ``n`` months after the series, with their planned promotion."""
    return _frame(N_STEPS + n).iloc[N_STEPS:][["date", "promo"]].reset_index(drop=True)


@pending("8")
def test_a_run_that_used_exogenous_declares_what_its_prediction_needs(
    client, exogenous_run
):
    response = client.get(f"/api/v1/predict/splits/{exogenous_run}")

    assert response.status_code == 200, response.text
    assert response.json()["exogenous"] == {
        "columns": [{"name": "promo", "type": "Float"}]
    }


@pending("8")
def test_a_dataset_of_future_rows_is_forecast_with_its_exogenous_values(
    client, tmp_path, exogenous_run
):
    from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

    future = _future()
    dataset_id = _upload(client, future, tmp_path, "future")
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "dataset_id": dataset_id}
    )
    assert response.status_code == 200, response.text
    PredictJob(prediction_id=response.json()["id"]).run()
    prediction = _get(client, Prediction, response.json()["id"])

    assert prediction.status == PredictionStatus.FINISHED
    saved = load_dataset(str(Path(prediction.results_path) / "dataset")).to_pandas()
    assert list(saved["promo"]) == list(future["promo"])
    assert len(saved) == len(future)


@pending("8")
def test_a_future_that_misses_a_date_of_the_grid_is_refused_with_the_date(
    client, tmp_path, exogenous_run
):
    from DashAI.back.job.base_job import JobError

    dataset_id = _upload(client, _future().drop(index=1), tmp_path, "gap")
    response = client.post(
        "/api/v1/predict/", json={"run_id": exogenous_run, "dataset_id": dataset_id}
    )
    assert response.status_code == 200, response.text

    with pytest.raises(JobError, match="2024-02-01"):
        PredictJob(prediction_id=response.json()["id"]).run()


@pending("8")
def test_a_manual_future_starts_from_the_next_dates_of_the_grid(client, exogenous_run):
    response = client.get(
        f"/api/v1/predict/future-dates/{exogenous_run}", params={"horizon": 2}
    )

    assert response.status_code == 200, response.text
    assert response.json()["dates"] == ["2024-01-01", "2024-02-01"]


@pending("8")
def test_a_manual_future_is_forecast_through_the_job(client, exogenous_run):
    response = client.post("/api/v1/predict/", json={"run_id": exogenous_run})
    assert response.status_code == 200, response.text
    rows = [
        {"date": "2024-01-01", "promo": 1.0},
        {"date": "2024-02-01", "promo": 0.0},
    ]

    PredictJob(prediction_id=response.json()["id"], manual_input_data=rows).run()

    prediction = _get(client, Prediction, response.json()["id"])
    assert prediction.status == PredictionStatus.FINISHED
