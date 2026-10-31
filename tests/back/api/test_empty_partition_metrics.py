"""A metric asked for on a partition that ends up with no rows.

The session wizard picks each partition's metrics from the partitions the
splitter's preview says receive rows. A splitter with no preview, or a preview
that could not be computed, leaves the wizard on the partitions the strategy
scores (``scored_splits``), so a session can ask for metrics on a partition
the splitter leaves empty: a holdout with no test, folds with no reserved
test. Neither the session API nor the run may fail on it.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures.
"""

import json

import pytest

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.job.model_job import ModelJob

METRICS = ["MAE", "RMSE"]


@pytest.mark.parametrize(
    ("strategy", "splits"),
    [
        (
            "HoldoutEvaluationStrategy",
            {
                "splitter_name": "HoldoutSplitter",
                "splitType": "random",
                "train": 0.8,
                "validation": 0.2,
                "test": 0,
                "shuffle": True,
                "random_state": 0,
            },
        ),
        (
            "CrossValidationEvaluationStrategy",
            {
                "splitter_name": "KFoldSplitter",
                "splitType": "cv",
                "n_splits": 3,
                "test_size": 0,
                "shuffle": True,
                "random_state": 0,
            },
        ),
    ],
    ids=["holdout without test", "folds without a reserved test"],
)
def test_metrics_asked_for_an_empty_partition_have_no_value(
    client, dataset_1, strategy, splits
):
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_1.id,
            "task_name": "RegressionTask",
            "name": f"empty-partition-{strategy}",
            "column_roles": {
                "features": [
                    {"kind": "raw", "name": "SepalLengthCm"},
                    {"kind": "raw", "name": "SepalWidthCm"},
                ],
                "target": [{"kind": "raw", "name": "PetalWidthCm"}],
            },
            "train_metrics": METRICS,
            "validation_metrics": METRICS,
            "test_metrics": METRICS,
            "evaluation_strategy": strategy,
            "splits": json.dumps(splits),
            "preprocessing": [],
        },
    )
    assert response.status_code == 201, response.text

    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": response.json()["id"],
            "model_name": "LinearRegression",
            "name": f"empty-partition-{strategy}",
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
        },
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]

    ModelJob(run_id=run_id).run()

    run = client.get(f"/api/v1/run/{run_id}").json()
    assert run["status"] == RunStatus.FINISHED.value
    assert set(run["validation_metrics"]) == set(METRICS)
    # The test partition has no rows, so its metrics have no value at all.
    assert not run["test_metrics"]
