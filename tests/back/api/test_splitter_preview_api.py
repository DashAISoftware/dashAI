"""POST /splitter/preview: the split preview the session wizard draws.

The splitter computes it (``BaseSplitter.preview``, checked on the wizard's own
cases in ``tests/back/splitters/test_split_preview.py``); the endpoint reads the
dataset the wizard is splitting, so the wizard counts no rows itself.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CASES = {
    case["name"]: case
    for case in json.loads(
        (
            Path(__file__).parents[3]
            / "DashAI"
            / "front"
            / "src"
            / "components"
            / "models"
            / "modelSession"
            / "__fixtures__"
            / "splitPreviewCases.json"
        ).read_text(encoding="utf-8")
    )
}


def _preview(client: TestClient, dataset_id, splitter_name, params, **extra):
    return client.post(
        "/api/v1/splitter/preview",
        json={
            "dataset_id": dataset_id,
            "splitter_name": splitter_name,
            "params": params,
            **extra,
        },
    )


def test_a_random_holdout_is_previewed_on_the_dataset_rows(client, dataset_1):
    case = CASES["random holdout, three partitions"]

    response = _preview(
        client, dataset_1.id, "HoldoutSplitter", case["params"], split_type="random"
    )

    assert response.status_code == 200, response.text
    body = response.json()
    for key in ("rows", "notes", "shares", "errors", "partitions"):
        assert body[key] == case["expected"][key], key


def test_more_folds_than_rows_is_an_error_of_the_preview(client, dataset_1):
    response = _preview(client, dataset_1.id, "KFoldSplitter", {"n_splits": 200})

    assert response.status_code == 200, response.text
    assert response.json()["errors"] == [
        {"key": "foldsMustBeLessThanDatasetSize", "values": {"datasetSize": 150}}
    ]


def test_a_predefined_split_reads_the_dataset_own_partitions(client, dataset_1):
    # The iris dataset carries no partitions of its own, so a predefined split
    # gives none, whatever indexes the request sends.
    response = _preview(
        client,
        dataset_1.id,
        "HoldoutSplitter",
        {},
        split_type="predefined",
        indexes={"train": [0, 1], "validation": [], "test": [2]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["partitions"] == []


def test_a_backtest_is_previewed_on_the_dataset_steps(client, dataset_1):
    response = _preview(
        client, dataset_1.id, "RollingOriginSplitter", {"horizon": 6, "n_origins": 3}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["errors"] == []
    assert body["partitions"] == ["validation", "test"]
    assert body["shares"] == {
        "train": 126 / 150,
        "validation": 18 / 150,
        "test": 6 / 150,
    }
    assert body["legend"] == [
        {"role": "train", "key": "steps", "values": {"count": 126}},
        {"role": "validation", "key": "steps", "values": {"count": 18}},
        {"role": "test", "key": "steps", "values": {"count": 6}},
    ]


def test_a_series_too_short_is_an_error_of_the_preview(client, dataset_1):
    response = _preview(
        client, dataset_1.id, "RollingOriginSplitter", {"horizon": 50, "n_origins": 2}
    )

    assert response.status_code == 200, response.text
    assert response.json()["errors"] == [
        {
            "key": "seriesTooShort",
            "values": {"needed": 151, "rows": 150, "horizon": 50, "origins": 2},
        }
    ]


@pytest.mark.parametrize(
    ("splitter_name", "detail"),
    [
        ("NoSuchSplitter", "Splitter NoSuchSplitter not found"),
        ("HoldoutEvaluationStrategy", "Splitter HoldoutEvaluationStrategy not found"),
    ],
)
def test_an_unknown_splitter_is_not_found(client, dataset_1, splitter_name, detail):
    response = _preview(client, dataset_1.id, splitter_name, {})

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == detail


def test_an_unknown_dataset_is_not_found(client):
    response = _preview(client, 99999, "HoldoutSplitter", {"train": 1})

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Dataset not found"


@pytest.mark.parametrize(
    ("splitter_name", "params", "field"),
    [
        ("RollingOriginSplitter", {"horizon": 6, "n_origins": 0}, "n_origins"),
        ("RollingOriginSplitter", {"horizon": 6, "n_origins": -1}, "n_origins"),
        # One origin is the temporal holdout; the session refuses it here.
        ("RollingOriginSplitter", {"horizon": 6, "n_origins": 1}, "n_origins"),
        ("RollingOriginSplitter", {"horizon": 0, "n_origins": 3}, "horizon"),
        ("TemporalHoldoutSplitter", {"horizon": 0}, "horizon"),
        ("TemporalHoldoutSplitter", {"horizon": -2}, "horizon"),
    ],
)
def test_a_backtest_the_session_would_refuse_is_refused_by_the_preview(
    client, dataset_1, splitter_name, params, field
):
    response = _preview(client, dataset_1.id, splitter_name, params)

    assert response.status_code == 422, response.text
    assert field in response.json()["detail"]


@pytest.fixture(name="dataset_info_reads")
def count_dataset_info_reads(monkeypatch):
    """Count the reads of the dataset's splits.json, every index list in it."""
    from DashAI.back.dataloaders.classes import dashai_dataset

    reads = []
    real = dashai_dataset.get_dataset_info

    def counted(path):
        reads.append(path)
        return real(path)

    monkeypatch.setattr(dashai_dataset, "get_dataset_info", counted)
    return reads


@pytest.mark.parametrize(
    ("splitter_name", "params", "extra"),
    [
        ("HoldoutSplitter", CASES["random holdout, three partitions"]["params"], {}),
        ("KFoldSplitter", {"n_splits": 5}, {}),
        ("RollingOriginSplitter", {"horizon": 6, "n_origins": 3}, {}),
    ],
    ids=["random", "folds", "backtest"],
)
def test_a_preview_counts_the_rows_without_reading_the_splits_file(
    client, dataset_1, dataset_info_reads, splitter_name, params, extra
):
    split_type = "random" if splitter_name == "HoldoutSplitter" else None

    response = _preview(
        client, dataset_1.id, splitter_name, params, split_type=split_type
    )

    assert response.status_code == 200, response.text
    assert dataset_info_reads == []


def test_a_predefined_preview_reads_the_dataset_partitions_once(
    client, dataset_1, dataset_info_reads
):
    response = _preview(
        client, dataset_1.id, "HoldoutSplitter", {}, split_type="predefined"
    )

    assert response.status_code == 200, response.text
    assert len(dataset_info_reads) == 1


def test_a_dataset_without_a_row_count_is_counted_from_its_splits_file(
    client, dataset_1, dataset_info_reads
):
    from DashAI.back.dependencies.database.models import Dataset

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        dataset = db.get(Dataset, dataset_1.id)
        total_rows, dataset.total_rows = dataset.total_rows, None
        db.commit()
    try:
        response = _preview(client, dataset_1.id, "KFoldSplitter", {"n_splits": 200})
    finally:
        with session_factory() as db:
            db.get(Dataset, dataset_1.id).total_rows = total_rows
            db.commit()

    assert response.status_code == 200, response.text
    assert len(dataset_info_reads) == 1
    assert response.json()["errors"] == [
        {"key": "foldsMustBeLessThanDatasetSize", "values": {"datasetSize": 150}}
    ]


def test_the_preview_does_not_block_the_event_loop():
    # It reads the database and, for a predefined split, a file: run in the
    # threadpool rather than on the event loop every other request waits on.
    import inspect

    from DashAI.back.api.api_v1.endpoints.splitters import preview_split

    assert not inspect.iscoroutinefunction(preview_split)


def test_parameters_the_splitter_cannot_read_are_refused(client, dataset_1):
    response = _preview(
        client, dataset_1.id, "RollingOriginSplitter", {"horizon": "six"}
    )

    assert response.status_code == 422, response.text


def _create_session(client: TestClient, dataset_id, strategy, splits):
    return client.post(
        "/api/v1/model-session/",
        json={
            "name": f"preview parity {strategy}",
            "dataset_id": dataset_id,
            "task_name": "TabularClassificationTask",
            "column_roles": {
                "features": [{"kind": "raw", "name": "SepalLengthCm"}],
                "target": [{"kind": "raw", "name": "Species"}],
            },
            "train_metrics": [],
            "validation_metrics": [],
            "test_metrics": [],
            "evaluation_strategy": strategy,
            "splits": json.dumps(splits),
        },
    )


def test_a_configuration_the_session_would_refuse_is_refused_by_the_preview(
    client, dataset_1
):
    # 25 folds fit in 150 rows, so the preview draws them; the schema caps
    # the folds at 20, so creating the session refuses them.
    params = {"n_splits": 25, "shuffle": True, "random_state": 42}

    created = _create_session(
        client,
        dataset_1.id,
        "CrossValidationEvaluationStrategy",
        {"splitter_name": "KFoldSplitter", "splitType": "cv", **params},
    )
    previewed = _preview(client, dataset_1.id, "KFoldSplitter", params)

    assert created.status_code == 422, created.text
    assert previewed.status_code == 422, previewed.text
    assert "n_splits" in previewed.json()["detail"]


def test_a_manual_split_is_checked_without_the_proportions_it_does_not_use(
    client, dataset_1
):
    # The form keeps the proportions of the random mode, and the session
    # payload of an index mode drops them, so they cannot refuse the preview.
    params = {"train": 0.9, "validation": 0.5, "test": 0.5}
    indexes = {"train": [0, 1, 2], "validation": [3], "test": [4]}

    created = _create_session(
        client,
        dataset_1.id,
        "HoldoutEvaluationStrategy",
        {
            "splitter_name": "HoldoutSplitter",
            "splitType": "manual",
            "splitted_indexes": {
                "train_indexes": indexes["train"],
                "val_indexes": indexes["validation"],
                "test_indexes": indexes["test"],
            },
        },
    )
    previewed = _preview(
        client,
        dataset_1.id,
        "HoldoutSplitter",
        params,
        split_type="manual",
        indexes=indexes,
    )

    assert created.status_code == 201, created.text
    assert previewed.status_code == 200, previewed.text
    assert previewed.json()["errors"] == []
