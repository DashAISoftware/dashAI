"""What a session declares about its exogenous variables before training.

``GET /model-session/{id}/exogenous-use`` says, for every model the session's
task offers, whether a run of it would read the exogenous variables and why
not (RECONCILING_FORECASTING §2.14, detail 2). ``POST /run/`` refuses a model
that requires them in a session without them, before anything trains.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import pytest

from DashAI.back.models.forecasting.naive import NaiveForecaster
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    EXOGENOUS_REQUIRED,
)
from tests.back.api.test_forecasting_acceptance import _monthly, _session
from tests.back.api.test_forecasting_exogenous_acceptance import (
    PROMO,
    _frame,
)
from tests.back.api.test_forecasting_exogenous_acceptance import (
    _session as _exogenous_session,
)


class RequiringForecaster(NaiveForecaster):
    """A forecaster that cannot run without exogenous variables."""

    EXOGENOUS = EXOGENOUS_REQUIRED


@pytest.fixture(name="requiring")
def register_a_model_that_requires_them(client):
    registry = client.app.container["component_registry"]
    registry.register_component(RequiringForecaster)
    yield RequiringForecaster
    registry.unregister_component(RequiringForecaster)


def _run_body(session_id, model):
    return {
        "model_session_id": session_id,
        "model_name": model,
        "name": f"{model} of {session_id}",
        "parameters": {},
        "optimizer_name": "",
        "optimizer_parameters": {},
        "plot_history_path": "",
        "plot_slice_path": "",
        "plot_contour_path": "",
        "plot_importance_path": "",
        "goal_metric": "",
        "description": "",
        "nested": None,
    }


def _declared(client, session_id):
    response = client.get(f"/api/v1/model-session/{session_id}/exogenous-use")
    assert response.status_code == 200, response.text
    return response.json()


def test_every_offered_model_is_marked_in_a_session_with_exogenous(client, tmp_path):
    declared = _declared(client, _exogenous_session(client, tmp_path, exogenous=PROMO))

    assert declared["has_exogenous"] is True
    assert [m["model"] for m in declared["models"]] == [
        "ARIMA",
        "DriftForecaster",
        "ExponentialSmoothing",
        "MeanForecaster",
        "NaiveForecaster",
        "SeasonalNaiveForecaster",
        "Theta",
    ]
    by_model = {m["model"]: m for m in declared["models"]}
    assert by_model["ARIMA"] == {
        "model": "ARIMA",
        "uses": True,
        "reason": None,
        "switch": "use_exogenous",
    }
    assert by_model["ExponentialSmoothing"] == {
        "model": "ExponentialSmoothing",
        "uses": False,
        "reason": {
            "key": "modelTakesNoExogenous",
            "values": {"model": "ExponentialSmoothing"},
        },
        "switch": None,
    }


def test_a_session_without_exogenous_says_so_for_every_model(client, tmp_path):
    declared = _declared(client, _session(client, tmp_path, _monthly()))

    assert declared["has_exogenous"] is False
    assert {m["reason"]["key"] for m in declared["models"]} == {"sessionHasNoExogenous"}


def test_a_task_without_exogenous_variables_marks_no_model(client, dataset_1):
    import json

    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "TabularClassificationTask",
            "name": "no-exogenous",
            "column_roles": {
                "features": [{"kind": "raw", "name": "SepalLengthCm"}],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps({"train": 0.6, "validation": 0.2, "test": 0.2}),
            "preprocessing": [],
        },
    )
    assert response.status_code == 201, response.text

    assert _declared(client, response.json()["id"]) == {
        "has_exogenous": False,
        "models": [],
    }


def test_a_model_that_requires_them_is_refused_without_them(
    client, tmp_path, requiring
):
    session_id = _session(client, tmp_path, _monthly())

    response = client.post(
        "/api/v1/run/", json=_run_body(session_id, requiring.__name__)
    )

    assert response.status_code == 422, response.text
    assert "requires exogenous variables" in response.json()["detail"]


def test_a_model_that_requires_them_is_taken_with_them(client, tmp_path, requiring):
    session_id = _exogenous_session(client, tmp_path, _frame(), exogenous=PROMO)

    response = client.post(
        "/api/v1/run/", json=_run_body(session_id, requiring.__name__)
    )

    assert response.status_code == 201, response.text


def test_a_model_that_requires_them_is_refused_switched_off(
    client, tmp_path, requiring
):
    """The 422 reads the run's decision, the same the units act on: a model
    that needs them and is told not to read them would fail training."""
    session_id = _exogenous_session(client, tmp_path, _frame(), exogenous=PROMO)
    body = _run_body(session_id, requiring.__name__)
    body["parameters"] = {"use_exogenous": False}

    response = client.post("/api/v1/run/", json=body)

    assert response.status_code == 422, response.text
    assert "requires exogenous variables" in response.json()["detail"]
