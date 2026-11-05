"""Regression net for the session preprocessing of the x/y tasks.

Written before the exogenous PR (RECONCILING_FORECASTING §7) and recorded on
its base, develop ``182120b0a``, with
``DASHAI_RECORD_SESSION_PREPROCESSING_NET=1``. That PR gives
``PreprocessingJob`` a branch for the backtest's cuts and ``infer_structure``
a rule for tasks that must keep their rows. Neither may touch an x/y session,
and this pins what one sees, holdout and K-fold with a reserved test:

- the artifacts the job writes, and what each one was fitted on. A fitted
  ``SessionPreprocessor`` does not say which rows it saw, so each is pinned
  by what it makes of the whole dataset: the imputer's mean, the scaler's
  scale and the encoder's categories all show in those values;
- the columns each artifact resolved, and the roles the session stores;
- the run's partitions and metric rows;
- the estimated structure of chains with a step that changes rows.

The chain covers what an exogenous column will go through: an imputer, a
scaler, a one-hot encoder on a ``Categorical`` and ``DateFeaturesConverter``
dropping its date.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob
from tests.back.api.golden_net import Golden
from tests.back.api.test_column_roles_net import _metrics, _split_indexes
from tests.back.api.test_forecasting_acceptance import _get

GOLDEN = Golden(
    Path(__file__).with_name("session_preprocessing_net_golden.json"),
    "DASHAI_RECORD_SESSION_PREPROCESSING_NET",
)

N_ROWS = 60
COLORS = ["red", "green", "blue"]
TYPES = {
    "num_a": {"type": "Float", "dtype": "float64"},
    "num_b": {"type": "Float", "dtype": "float64"},
    "color": {"type": "Categorical", "dtype": "string"},
    "day": {"type": "Date", "dtype": "%Y-%m-%d"},
    "y": {"type": "Float", "dtype": "float64"},
    "label": {"type": "Categorical", "dtype": "string"},
}

CHAIN = [
    {
        "converter": "SimpleImputer",
        "params": {"strategy": "mean"},
        "scope": [{"kind": "raw", "name": "num_a"}],
    },
    {
        "converter": "StandardScaler",
        "params": {},
        "scope": [{"kind": "raw", "name": "num_b"}],
    },
    {
        "converter": "OneHotEncoder",
        "params": {},
        "scope": [{"kind": "raw", "name": "color"}],
    },
    {
        "converter": "DateFeaturesConverter",
        "params": {"drop_source_columns": True},
        "scope": [{"kind": "raw", "name": "day"}],
    },
]
#: The imputer and the scaler replace their columns in place, under their own
#: names, so the model reads them as raw refs; the encoder and the date
#: features add columns, read as their step's group.
FEATURES = [
    {"kind": "raw", "name": "num_a"},
    {"kind": "raw", "name": "num_b"},
    {"kind": "group", "step": 2},
    {"kind": "group", "step": 3},
]

#: By index, so what each artifact was fitted on is known.
HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "train": list(range(36)),
    "validation": list(range(36, 48)),
    "test": list(range(48, N_ROWS)),
}
KFOLD = {
    "splitter_name": "KFoldSplitter",
    "n_splits": 3,
    "test_size": 0.2,
    "is_random": True,
    "has_changed": True,
    "seed": 0,
    "shuffle": False,
    "stratify": False,
}
STRATEGIES = {
    "holdout": ("HoldoutEvaluationStrategy", HOLDOUT),
    "kfold": ("CrossValidationEvaluationStrategy", KFOLD),
}


def frame() -> pd.DataFrame:
    steps = np.arange(N_ROWS)
    num_a = 10.0 + 0.5 * steps
    num_a[[3, 17, 40, 55]] = np.nan
    return pd.DataFrame(
        {
            "num_a": num_a,
            "num_b": 100.0 + 7.0 * np.cos(steps),
            "color": [COLORS[(i * 7) % 3] for i in range(N_ROWS)],
            "day": pd.date_range("2021-03-01", periods=N_ROWS, freq="5D").strftime(
                "%Y-%m-%d"
            ),
            "y": 3.0 + 0.2 * steps + np.sin(steps),
            "label": ["yes" if i % 3 else "no" for i in range(N_ROWS)],
        }
    )


def upload(client, directory: Path, name: str, data: pd.DataFrame) -> int:
    path = directory / f"{name}.csv"
    data.to_csv(path, index=False)
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
                    "inferred_types": {c: TYPES[c] for c in data.columns},
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def create_session(client, dataset_id: int, strategy: str) -> int:
    name, splits = STRATEGIES[strategy]
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "RegressionTask",
            "name": f"preprocessing-net-{strategy}-{dataset_id}",
            "column_roles": {
                "features": FEATURES,
                "target": [{"kind": "raw", "name": "y"}],
            },
            "train_metrics": [],
            "validation_metrics": ["MAE", "RMSE"],
            "test_metrics": ["MAE", "RMSE"],
            "evaluation_strategy": name,
            "splits": json.dumps(splits),
            "preprocessing": CHAIN,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["preprocessing_status"] == "ready", response.text
    return response.json()["id"]


def train(client, session_id: int) -> int:
    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session_id,
            "model_name": "LinearRegression",
            "name": f"linear of {session_id}",
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
    assert _get(client, Run, run_id).status == RunStatus.FINISHED
    return run_id


def _rounded(data: pd.DataFrame) -> dict:
    out = {}
    for column in data.columns:
        values = data[column].tolist()
        out[column] = [
            round(v, 9) if isinstance(v, float) and not np.isnan(v) else v
            for v in values
        ]
    return out


def _artifacts(session: ModelSession, dataset) -> dict:
    """Every artifact, by what it resolved and makes of the whole dataset."""
    directory = session.preprocessing_artifacts_path
    pinned = {}
    for name in sorted(os.listdir(directory)):
        with open(os.path.join(directory, name), "rb") as f:
            preprocessor = pickle.load(f)
        transformed = preprocessor.transform_dataset(dataset)
        pinned[name] = {
            "resolved_columns": preprocessor.resolved_columns,
            "resolved_slots": preprocessor.resolved_slots,
            "columns": transformed.column_names,
            "values": _rounded(transformed.to_pandas()),
        }
    return pinned


@pytest.fixture(scope="module", name="dataset_id")
def fixture_dataset_id(client, tmp_path_factory):
    return upload(
        client, tmp_path_factory.mktemp("preprocessing-net"), "prep-net", frame()
    )


@pytest.fixture(scope="module", autouse=True)
def _save_golden():
    yield
    GOLDEN.save()


@pytest.fixture(scope="module", name="trained")
def fixture_trained(client, dataset_id):
    trained = {}
    for strategy in STRATEGIES:
        session_id = create_session(client, dataset_id, strategy)
        trained[strategy] = (session_id, train(client, session_id))
    return trained


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_the_job_writes_the_same_artifacts(client, dataset_id, trained, strategy):
    session = _get(client, ModelSession, trained[strategy][0])
    stored = _get(client, Dataset, dataset_id)
    dataset = load_dataset(f"{stored.file_path}/dataset")

    GOLDEN.pin(f"{strategy}/artifacts", _artifacts(session, dataset))


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_the_session_stores_the_same_roles(client, trained, strategy):
    session = _get(client, ModelSession, trained[strategy][0])

    GOLDEN.pin(
        f"{strategy}/session",
        {
            "column_roles": session.column_roles,
            "preprocessing": session.preprocessing,
            "preprocessing_status": session.preprocessing_status,
        },
    )


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_the_run_partitions_and_scores_the_same(client, trained, strategy):
    run_id = trained[strategy][1]

    GOLDEN.pin(
        f"{strategy}/run",
        {"split_indexes": _split_indexes(client, run_id)},
    )
    GOLDEN.pin(f"{strategy}/metrics", _metrics(client, run_id))


ROW_CHAINS = {
    "regression_nan_remover": (
        "RegressionTask",
        {"features": ["num_a", "num_b"], "target": ["y"]},
        [
            {
                "converter": "NanRemover",
                "params": {},
                "scope": [{"kind": "raw", "name": "num_a"}],
            }
        ],
    ),
    "classification_sampler": (
        "TabularClassificationTask",
        {"features": ["num_a", "num_b"], "target": ["label"]},
        [
            {
                "converter": "SimpleImputer",
                "params": {"strategy": "mean"},
                "scope": [{"kind": "raw", "name": "num_a"}],
            },
            {
                "converter": "RandomUnderSamplerConverter",
                "params": {},
                "scope": [
                    {"kind": "raw", "name": "num_a"},
                    {"kind": "raw", "name": "num_b"},
                ],
            },
        ],
    ),
    "regression_chain": (
        "RegressionTask",
        {"features": ["num_a", "num_b", "color", "day"], "target": ["y"]},
        CHAIN,
    ),
}


@pytest.mark.parametrize("chain", ROW_CHAINS)
def test_the_estimated_structure_is_the_same(client, dataset_id, chain):
    task_name, roles, steps = ROW_CHAINS[chain]
    response = client.post(
        "/api/v1/model-session/preprocessing/structure",
        json={
            "dataset_id": dataset_id,
            "task_name": task_name,
            "column_roles": roles,
            "steps": steps,
        },
    )

    assert response.status_code == 200, response.text
    GOLDEN.pin(f"structure/{chain}", response.json())
