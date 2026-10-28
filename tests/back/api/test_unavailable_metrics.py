"""A metric with no value on a run's data is recorded as unavailable, and why.

MAPE divides by each actual value, so on a partition with a zero it has none.
The run goes on: the metric's row holds a NULL value and the reason. Every
reader of ``Metric.value`` either leaves such a row out of what it formats as
numbers, or carries the reason along. Optimizing for such a metric stops the
run with an error that says so.

Lives under ``tests/back/api`` to reuse the ``client`` and ``dataset_1``
fixtures.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.dependencies.database.models import Dataset, Metric, Run
from DashAI.back.job.base_job import JobError
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from DashAI.back.metrics.forecasting.mape import MAPE
from DashAI.back.model_package.export import build_package
from DashAI.back.session_package.export import build_session_package
from DashAI.back.session_package.load import import_session_package
from tests.back.api.trained_runs import fit_regressor

REASON = "MAPE divides by each actual value, and 1 of them are zero."


def _session_factory(client):
    return client.app.container["session_factory"]


def _add(client, run_id, rows):
    with _session_factory(client)() as db:
        db.add_all(
            Metric(
                run_id=run_id,
                split=split,
                level=level,
                name=name,
                value=value,
                unavailable_reason=None if value is not None else REASON,
                step=0,
                fold_index=fold,
            )
            for split, level, name, value, fold in rows
        )
        db.commit()


@pytest.fixture(scope="module", name="run_id")
def a_finished_run_with_an_unavailable_metric(
    client: TestClient, dataset_1: Dataset, tmp_path_factory
):
    run_id = fit_regressor(
        client,
        dataset_1,
        tmp_path_factory.mktemp("unavailable-metrics"),
        "unavailable-metrics-session",
    )
    _add(
        client,
        run_id,
        [
            (SplitEnum.TEST, LevelEnum.LAST, "MAE", 0.5, None),
            (SplitEnum.TEST, LevelEnum.LAST, "MAPE", None, None),
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAE", 0.4, 0),
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAE", 0.6, 1),
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAPE", 12.0, 0),
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAPE", None, 1),
        ],
    )
    return run_id


# --- the readers of Metric.value --------------------------------------------


def test_the_run_carries_the_reason_beside_its_numbers(client, run_id):
    run = client.get(f"/api/v1/run/{run_id}").json()

    assert run["test_metrics"] == {"MAE": 0.5}
    assert run["test_metrics_unavailable"] == {"MAPE": REASON}
    assert run["validation_metrics_unavailable"] is None


def test_the_fold_lists_leave_out_a_metric_with_a_hole(client, run_id):
    response = client.get(f"/api/v1/run/{run_id}/fold-metrics")

    assert response.status_code == 200
    assert response.json() == {"MAE": [0.4, 0.6]}


def test_a_run_with_no_fold_value_has_no_fold_metrics(
    client, dataset_1, tmp_path_factory
):
    # MAPE alone, on a series with a zero in every fold: the lists would all
    # be left out, and an empty answer reads as "no metric" to a client that
    # then pairs nothing. It is the documented 404, as for a run with no rows.
    other = fit_regressor(
        client,
        dataset_1,
        tmp_path_factory.mktemp("no-fold-value"),
        "no-fold-value-session",
    )
    _add(
        client,
        other,
        [
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAPE", None, 0),
            (SplitEnum.VALIDATION, LevelEnum.FOLD, "MAPE", None, 1),
        ],
    )

    response = client.get(f"/api/v1/run/{other}/fold-metrics")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "No fold metrics found for this run"


def test_the_live_metrics_send_no_row_without_a_value(client, run_id):
    with client.websocket_connect(f"/api/v1/metrics/ws/{run_id}") as websocket:
        payload = json.loads(websocket.receive_text())

    assert "MAPE" not in payload["TEST"]["LAST"]
    assert [point["value"] for point in payload["TEST"]["LAST"]["MAE"]] == [0.5]
    assert [point["value"] for point in payload["VALIDATION"]["FOLD"]["MAPE"]] == [12.0]


def test_the_model_package_lists_only_scores(client, run_id, tmp_path):
    container = client.app.container
    manifest = build_package(
        run_id,
        tmp_path / "model.zip",
        container["session_factory"],
        container["component_registry"],
    )

    assert manifest["info"]["test_metrics"] == {"MAE": 0.5}


def test_a_session_package_keeps_the_reason_through_a_round_trip(
    client, run_id, tmp_path
):
    container = client.app.container
    with _session_factory(client)() as db:
        session_id = db.get(Run, run_id).model_session_id
    package = tmp_path / "unavailable.dashai"
    build_session_package(
        session_id,
        [run_id],
        True,
        package,
        container["session_factory"],
        container["component_registry"],
    )

    result = import_session_package(
        package,
        container["session_factory"],
        container["component_registry"],
        container["config"],
        container["job_queue"],
    )

    def rows(db, of_run):
        return sorted(
            (
                (m.split.name, m.level.name, m.name, m.value, m.unavailable_reason)
                for m in db.query(Metric).filter(Metric.run_id == of_run)
            ),
            key=lambda row: [str(field) for field in row],
        )

    with _session_factory(client)() as db:
        (imported,) = db.query(Run).filter(Run.model_session_id == result["session_id"])
        assert rows(db, imported.id) == rows(db, run_id)
        assert ("TEST", "LAST", "MAPE", None, REASON) in rows(db, imported.id)


# --- a regression run that scores MAPE on a zero -----------------------------

ZERO_TARGET = pd.DataFrame(
    {
        "x": np.arange(30, dtype=float),
        # Two zeros in the last rows, which the unshuffled holdout keeps for
        # validation (rows 24 to 29) and the third fold validates on.
        "y": [float(2 * v + 1) for v in range(26)] + [0.0, 55.0, 0.0, 59.0],
    }
)
NO_SHUFFLE_HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "splitType": "random",
    "train": 0.6,
    "test": 0.2,
    "validation": 0.2,
    "shuffle": False,
    "stratify": False,
    "seed": 0,
}
NO_SHUFFLE_KFOLD = {
    "splitter_name": "KFoldSplitter",
    "n_splits": 3,
    "test_size": 0.0,
    "shuffle": False,
    "random_state": 0,
}


def _upload(client, directory: Path, name: str) -> int:
    path = directory / f"{name}.csv"
    ZERO_TARGET.to_csv(path, index=False)
    with _session_factory(client)() as db:
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
                    "inferred_types": {
                        "x": {"type": "Float", "dtype": "float64"},
                        "y": {"type": "Float", "dtype": "float64"},
                    },
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _train(client, tmp_path, name, strategy, splits) -> int:
    dataset_id = _upload(client, tmp_path, name)
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "RegressionTask",
            "name": name,
            "column_roles": {
                "features": [{"kind": "raw", "name": "x"}],
                "target": [{"kind": "raw", "name": "y"}],
            },
            "train_metrics": [],
            # Not offered to regression by the wizard in this PR, but the
            # session API takes any metric name.
            "validation_metrics": ["MAE", "MAPE"],
            "test_metrics": ["MAE", "MAPE"],
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
            "name": name,
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
    return run_id


def test_a_holdout_run_records_mape_on_a_zero_as_unavailable(client, tmp_path):
    run_id = _train(
        client,
        tmp_path,
        "unavailable-holdout",
        "HoldoutEvaluationStrategy",
        NO_SHUFFLE_HOLDOUT,
    )

    run = client.get(f"/api/v1/run/{run_id}").json()
    assert run["status"] == RunStatus.FINISHED.value
    assert set(run["validation_metrics"]) == {"MAE"}
    assert "zero" in run["validation_metrics_unavailable"]["MAPE"]
    # The test rows have no zero, and MAPE is scored there as ever.
    assert set(run["test_metrics"]) == {"MAE", "MAPE"}


def test_a_cross_validation_run_has_no_mape_mean_over_a_fold_with_a_zero(
    client, tmp_path
):
    run_id = _train(
        client,
        tmp_path,
        "unavailable-kfold",
        "CrossValidationEvaluationStrategy",
        NO_SHUFFLE_KFOLD,
    )

    run = client.get(f"/api/v1/run/{run_id}").json()
    assert set(run["validation_metrics"]) == {"MAE"}
    assert "zero" in run["validation_metrics_unavailable"]["MAPE"]
    with _session_factory(client)() as db:
        folds = (
            db.query(Metric)
            .filter_by(run_id=run_id, level=LevelEnum.FOLD, name="MAPE")
            .order_by(Metric.fold_index)
            .all()
        )
    # The first two folds have a MAPE; the third validates on the zeros.
    assert [row.value is None for row in folds] == [False, False, True]


# --- optimizing for it -------------------------------------------------------


class _ConstantModel:
    """Fits nothing and predicts ones, which is all a trial needs here."""

    def train(self, *args, **kwargs):
        return self

    def predict(self, x):
        return np.ones(len(x))

    def prepare_output(self, y, is_fit=False):
        return y

    def calculate_metrics(self, *args, **kwargs):
        return None


def test_optimizing_for_a_metric_with_no_value_stops_the_run():
    from DashAI.back.units.fit_model_unit import FitModelUnit

    frame = to_dashai_dataset(pd.DataFrame({"y": [0.0, 2.0]}))
    xs = {"train": frame, "validation": frame}
    unit = FitModelUnit(
        optimizer={"component": "", "params": {}},
        goal_metric="MAPE",
        run_id=None,
        artifact_prefix=None,
        trial_splits=[],
    )

    with pytest.raises(JobError, match="optimization metric MAPE has no value"):
        unit._score_one_trial(_ConstantModel(), xs, xs, MAPE)
