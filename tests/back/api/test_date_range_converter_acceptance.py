"""Acceptance cases for the date range converter, written before the PR.

Each case states what the PR (RECONCILING_FORECASTING §9) has to deliver: a
dataset that only holds a series of values gets a date column in the notebook,
and can then be forecast. Each was a strict ``xfail`` until the slice that
delivered it, made to fail first for the reason it named (§9.7).

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.enums.status import ConverterStatus
from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_columns_spec,
    load_dataset,
)
from DashAI.back.dependencies.database.models import Converter, Dataset
from DashAI.back.job.base_job import JobError
from DashAI.back.job.converter_job import ConverterJob
from DashAI.back.job.dataset_job import DatasetJob
from tests.back.api.test_forecasting_acceptance import CV, ROLLING, TASK
from tests.back.api.test_forecasting_exogenous_acceptance import _train

#: Dataset and notebook names are unique, and several tests upload more than one.
_NAMES = itertools.count()

N_STEPS = 48


# --------------------------------------------------------------------------- #
# Datasets, notebooks and converters
# --------------------------------------------------------------------------- #


def _values(n: int = N_STEPS) -> pd.DataFrame:
    """A series with no date column: the values only, in time order."""
    steps = np.arange(n)
    return pd.DataFrame({"sales": 100.0 + 0.8 * steps + np.cos(steps)})


def _upload(client, frame: pd.DataFrame, directory: Path, types=None) -> int:
    types = {"sales": {"type": "Float", "dtype": "float64"}, **(types or {})}
    name = f"date-range-{next(_NAMES)}"
    directory.mkdir(parents=True, exist_ok=True)
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
                    "inferred_types": {c: types[c] for c in frame.columns},
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


def _notebook(client, dataset_id: int) -> dict:
    response = client.post(
        "/api/v1/notebook/",
        json={"dataset_id": dataset_id, "name": f"date-range-{next(_NAMES)}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _apply(client, notebook: dict, **params) -> int:
    """Add a DateRangeConverter with an empty scope and run it."""
    response = client.post(
        "/api/v1/converter/",
        json={
            "notebook_id": notebook["id"],
            "converter": "DateRangeConverter",
            "parameters": {
                "order": 0,
                "params": params,
                "scope": {"columns": [], "rows": []},
                "target": None,
            },
        },
    )
    assert response.status_code == 201, response.text
    converter_id = response.json()["id"]
    ConverterJob(converter_id=converter_id).run()
    return converter_id


def _dated_notebook(client, tmp_path, frame=None, types=None, **params) -> dict:
    dataset_id = _upload(client, _values() if frame is None else frame, tmp_path, types)
    notebook = _notebook(client, dataset_id)
    _apply(client, notebook, **params)
    return notebook


def _notebook_path(notebook: dict) -> str:
    return f"{notebook['file_path']}/dataset"


def _save_as_dataset(client, notebook: dict) -> int:
    """What the app does to turn a notebook into a dataset a session can use."""
    name = f"date-range-saved-{next(_NAMES)}"
    with client.app.container["session_factory"]() as db:
        entry = Dataset(name=name, file_path="")
        entry.set_status_as_delivered()
        db.add(entry)
        db.commit()
        db.refresh(entry)
        dataset_id = entry.id
    DatasetJob(
        job_type="DatasetJob",
        kwargs={
            "dataset_id": dataset_id,
            "url": "",
            "params": {"name": name},
            "notebook_id": notebook["id"],
            "file_path": None,
        },
    ).run()
    return dataset_id


def _error_chain(error: BaseException) -> str:
    """Every message in an exception and its causes, for wrapped job errors."""
    messages = []
    while error is not None:
        messages.append(str(error))
        error = error.__cause__ or error.__context__
    return " | ".join(messages)


# --------------------------------------------------------------------------- #
# Slice 2: one rule for what runs in a session
# --------------------------------------------------------------------------- #


def _converter_names(client, **params) -> set:
    response = client.get(
        "/api/v1/component/",
        params={"select_types": ["Converter"], "data_kind": "dataset", **params},
    )
    assert response.status_code == 200, response.text
    return {component["name"] for component in response.json()}


def test_the_session_catalog_leaves_out_what_only_runs_in_a_notebook(client):
    offered = _converter_names(client, in_session=True)

    assert "TimeResamplerConverter" not in offered
    assert "TimeSeriesWindowConverter" not in offered
    assert {"NanRemover", "SMOTEConverter"} <= offered


def test_a_notebook_only_converter_is_out_of_sessions(client):
    from DashAI.back.converters.simple_converters.column_remover import (
        ColumnRemover,
    )
    from DashAI.back.preprocessing.column_ref import ConverterStep, RawColumnRef
    from DashAI.back.preprocessing.structure import infer_structure

    class NotebookOnlyRemover(ColumnRemover):
        NOTEBOOK_ONLY = True

    registry = client.app.container["component_registry"]
    registry.register_component(NotebookOnlyRemover)
    try:
        assert "ColumnRemover" in _converter_names(client, in_session=True)
        assert "NotebookOnlyRemover" not in _converter_names(client, in_session=True)
        assert "NotebookOnlyRemover" in _converter_names(client)

        result = infer_structure(
            dataset_types=load_dataset_types(),
            candidates=["a", "b"],
            target=[],
            steps=[
                ConverterStep(
                    converter="NotebookOnlyRemover",
                    params={},
                    scope=[RawColumnRef(name="a")],
                )
            ],
            component_registry={"NotebookOnlyRemover": {"class": NotebookOnlyRemover}},
        )
        assert result.steps[0].error.code == "notebook_only"
    finally:
        registry.unregister_component(NotebookOnlyRemover)


def load_dataset_types():
    from DashAI.back.dataloaders.classes.dashai_dataset import (
        to_dashai_dataset,
        transform_dataset_with_schema,
    )

    frame = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    schema = {
        "a": {"type": "Integer", "dtype": "int64"},
        "b": {"type": "Integer", "dtype": "int64"},
    }
    return transform_dataset_with_schema(to_dashai_dataset(frame), schema).types


# --------------------------------------------------------------------------- #
# Slice 3: the converter
# --------------------------------------------------------------------------- #


def test_a_series_of_values_gets_a_date_column(client, tmp_path):
    frame = _values()
    notebook = _dated_notebook(client, tmp_path, frame)

    dataset = load_dataset(_notebook_path(notebook))
    spec = get_columns_spec(_notebook_path(notebook))
    assert dataset.column_names == ["sales", "date"]
    assert len(dataset) == N_STEPS
    assert spec["date"]["type"] == "Date"
    assert spec["date"]["dtype"] == "%Y-%m-%d"
    assert spec["sales"]["type"] == "Float"
    table = dataset.to_pandas()
    assert table["sales"].tolist() == pytest.approx(frame["sales"].tolist())
    expected = pd.date_range("2024-01-01", periods=N_STEPS, freq="D")
    assert table["date"].tolist() == list(expected.strftime("%Y-%m-%d"))


def test_a_name_already_taken_is_numbered(client, tmp_path):
    frame = _values(5).assign(date=["a", "b", "c", "d", "e"])
    notebook = _dated_notebook(
        client, tmp_path, frame, types={"date": {"type": "Text", "dtype": "string"}}
    )

    dataset = load_dataset(_notebook_path(notebook))
    spec = get_columns_spec(_notebook_path(notebook))
    assert dataset.column_names == ["sales", "date", "date_1"]
    assert dataset.to_pandas()["date"].tolist() == ["a", "b", "c", "d", "e"]
    assert spec["date"]["type"] == "Text"
    assert spec["date_1"]["type"] == "Date"


def test_milliseconds_come_back_on_their_grid(client, tmp_path):
    from DashAI.back.tasks.time_grid import validate_grid
    from DashAI.back.types.date_utils import parse_date_column

    notebook = _dated_notebook(
        client, tmp_path, _values(10), start_date="2024-01-01", frequency="ms"
    )

    spec = get_columns_spec(_notebook_path(notebook))
    date_format = spec["date"]["dtype"]
    assert date_format == "%Y-%m-%d %H:%M:%S.%f"
    table = load_dataset(_notebook_path(notebook)).to_pandas()
    grid = validate_grid(parse_date_column(table["date"], date_format), table["sales"])
    assert grid.freq == "ms"
    assert grid.n_steps == 10
    assert grid.first == pd.Timestamp("2024-01-01")


@pytest.mark.parametrize(
    ("n_rows", "params", "message"),
    [
        (2, {}, "at least 3 rows"),
        (10, {"frequency": "MS", "start_date": "2024-01-15"}, "2024-02-01"),
        (10, {"frequency": "-1D"}, "forward in time"),
    ],
    ids=["two-rows", "off-anchor", "backwards"],
)
def test_a_refusal_reaches_the_job_with_its_reason(
    client, tmp_path, n_rows, params, message
):
    dataset_id = _upload(client, _values(n_rows), tmp_path)
    notebook = _notebook(client, dataset_id)

    with pytest.raises(JobError) as excinfo:
        _apply(client, notebook, **params)

    assert message in _error_chain(excinfo.value)
    with client.app.container["session_factory"]() as db:
        converter = db.query(Converter).filter_by(notebook_id=notebook["id"]).one()
        assert converter.status == ConverterStatus.ERROR
    assert load_dataset(_notebook_path(notebook)).column_names == ["sales"]


def test_a_dated_series_is_forecast_and_dates_its_future(client, tmp_path):
    notebook = _dated_notebook(
        client, tmp_path, start_date="2020-01-01", frequency="MS"
    )
    dataset_id = _save_as_dataset(client, notebook)

    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": TASK,
            "name": f"date-range-{dataset_id}",
            "column_roles": {
                "time_index": [{"kind": "raw", "name": "date"}],
                "series": [{"kind": "raw", "name": "sales"}],
            },
            "train_metrics": [],
            "validation_metrics": ["MAE"],
            "test_metrics": ["MAE"],
            "evaluation_strategy": CV,
            "splits": json.dumps(ROLLING),
            "preprocessing": [],
        },
    )
    assert response.status_code == 201, response.text
    run_id = _train(client, response.json()["id"], "NaiveForecaster")

    response = client.get(
        f"/api/v1/predict/future-dates/{run_id}", params={"horizon": 2}
    )

    assert response.status_code == 200, response.text
    # 48 months from January 2020 end in December 2023.
    assert response.json() == {
        "time_index": "date",
        "dates": ["2024-01-01", "2024-02-01"],
    }
