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


def test_the_default_splitter_is_refused_for_the_forecasting_task(client, tmp_path):
    # U7 on the task itself, now that it is registered: a payload that names
    # no splitter falls back to HoldoutSplitter, which shuffles rows, and the
    # single-series task does not offer it. SeriesOnlyTask stands in for it in
    # test_session_splitter_validation.py, from before it was registered.
    dataset_id = _upload(client, _monthly(), tmp_path, "default-splitter")

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(
            dataset_id,
            strategy="ForecastingHoldoutEvaluationStrategy",
            splits={"horizon": 6},
        ),
    )

    assert response.status_code == 422, response.text
    assert (
        "splits names no splitter, and the default, HoldoutSplitter, is not "
        "available for task SingleSeriesForecastingTask"
    ) in response.json()["detail"]


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


@pytest.mark.parametrize(
    ("strategy", "splits", "extra"),
    [
        (
            "ForecastingHoldoutEvaluationStrategy",
            {
                "splitter_name": "TemporalHoldoutSplitter",
                "train": 0.6,
                "validation": 0.2,
                "test": 0.2,
            },
            "train",
        ),
        (
            "ForecastingCrossValidationEvaluationStrategy",
            {
                "splitter_name": "RollingOriginSplitter",
                "n_splits": 3,
                "horizon": 6,
                "step": 1,
                "test_size": 6,
            },
            "n_splits",
        ),
    ],
    ids=["holdout", "rolling"],
)
def test_a_payload_from_before_the_cuts_in_steps_is_refused(
    client, tmp_path, strategy, splits, extra
):
    # The keys the splitters took before they cut in steps would otherwise be
    # dropped without a word, and the session would run on the defaults.
    dataset_id = _upload(client, _monthly(), tmp_path, f"old-payload-{extra}")

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=strategy, splits=splits),
    )

    assert response.status_code == 422, response.text
    assert extra in response.text


def test_a_seed_in_the_payload_is_not_a_parameter_the_splitter_refuses(
    client, tmp_path
):
    # ``seed`` is a meta key, and the legacy translation to ``random_state``
    # only applies to a splitter whose schema has one.
    dataset_id = _upload(client, _monthly(), tmp_path, "seeded")
    splits = {**PAIRS[0][1], "seed": 42}

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=PAIRS[0][0], splits=splits),
    )

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("total_rows", ["recorded", "missing"])
def test_a_short_series_is_refused_by_its_row_count(
    client, tmp_path, monkeypatch, total_rows
):
    # The count is the dataset's own, when it has one, so no batch is read;
    # a dataset without it (from before the column was backfilled) is
    # counted from the file.
    from DashAI.back.dependencies.database.models import Dataset
    from tests.back.api.test_model_session_api import count_batch_reads

    dataset_id = _upload(client, _monthly(20), tmp_path, f"short-{total_rows}")
    with client.app.container["session_factory"]() as db:
        dataset = db.get(Dataset, dataset_id)
        assert dataset.total_rows == 20
        if total_rows == "missing":
            dataset.total_rows = None
        db.commit()
    reads = count_batch_reads(monkeypatch)

    response = client.post(
        "/api/v1/model-session/",
        json=_session_body(dataset_id, strategy=PAIRS[1][0], splits=PAIRS[1][1]),
    )

    assert response.status_code == 422, response.text
    assert "needs a series of at least 25 steps" in response.text
    # The size is checked before anything else reads the file, so the only
    # batch read is the count's, and only where the dataset has no total.
    assert reads == ([] if total_rows == "recorded" else [0])
