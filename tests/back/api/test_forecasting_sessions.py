"""A forecasting session is created through the API with a splitter of origins.

Both forecasting strategies take a splitter that cuts origins in steps
(``SPLITTER_PARTITIONING = "origins"``), which the session API checks as it
checks any pair. Lives under ``tests/back/api`` to reuse the ``client``
fixture.
"""

import json

import pytest

from tests.back.api.test_forecasting_acceptance import _monthly, _session_body, _upload

PAIRS = [
    (
        "ForecastingHoldoutEvaluationStrategy",
        {"splitter_name": "TemporalHoldoutSplitter", "horizon": 6},
    ),
    (
        "ForecastingCrossValidationEvaluationStrategy",
        {"splitter_name": "RollingOriginSplitter", "horizon": 6, "n_origins": 3},
    ),
]


@pytest.mark.parametrize(("strategy", "splits"), PAIRS, ids=["holdout", "cv"])
def test_each_forecasting_strategy_takes_its_splitter(
    client, tmp_path, strategy, splits
):
    dataset_id = _upload(client, _monthly(), tmp_path, f"session-{strategy}")

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=strategy, splits=splits),
    )

    assert response.status_code == 201, response.text
    assert (
        json.loads(response.json()["splits"])["splitter_name"]
        == (splits["splitter_name"])
    )


@pytest.mark.parametrize(
    "strategy", ["HoldoutEvaluationStrategy", "CrossValidationEvaluationStrategy"]
)
def test_an_ordinary_strategy_is_not_offered_to_forecasting(client, tmp_path, strategy):
    dataset_id = _upload(client, _monthly(), tmp_path, f"ordinary-{strategy}")

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=strategy, splits=PAIRS[0][1]),
    )

    assert response.status_code == 422, response.text


def test_a_splitter_of_rows_is_refused_by_a_forecasting_strategy(client, tmp_path):
    dataset_id = _upload(client, _monthly(), tmp_path, "rows-splitter")
    splits = {"splitter_name": "HoldoutSplitter", "train": 0.6, "test": 0.2}

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(
            dataset_id, strategy="ForecastingHoldoutEvaluationStrategy", splits=splits
        ),
    )

    assert response.status_code == 422, response.text
    assert "is not available for task SingleSeriesForecastingTask" in response.text


def test_the_shortest_series_for_the_cuts_is_accepted(client, tmp_path):
    # Three origins and the test, six steps each, after one step to fit on.
    dataset_id = _upload(client, _monthly(25), tmp_path, "shortest")

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(
            dataset_id,
            strategy="ForecastingCrossValidationEvaluationStrategy",
            splits=PAIRS[1][1],
        ),
    )

    assert response.status_code == 201, response.text
