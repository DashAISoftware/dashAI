"""Regression net for rewriting the forecasting core.

Written before the rewrite and recorded against the code it replaces, so the
rewrite has something exact to be measured against. It pins three things that
must not move:

- **The point forecasts of the four models** on clean series. The rewrite
  takes dates out of the models and puts intervals in, and neither may change
  a forecast on a series that sits on its grid.
- **The notebook's series pieces**: the resampler, the calendar features, the
  window converter, the decomposition and the correlogram. They are the other
  route to a forecast, and the rewrite moves code they sit next to.
- **The windowed route through a regression session**, end to end. It is the
  route a user takes today, and the rewrite touches the regression metrics.

**One helper knows a model's API**: ``_forecast``. It is the only part of this
file the rewrite of the model contract may change. The values live in
``forecasting_core_net_golden.json``, recorded on the base with
``DASHAI_RECORD_FORECASTING_CORE_NET=1`` and never re-recorded with the
rewritten code: a diff on that file is a behaviour change.

Floats are compared to a relative 1e-9, as in ``test_column_roles_net.py``,
because the last digits of a statsmodels fit differ between platforms.

Lives under ``tests/back/api`` to reuse the ``client`` fixture from this
package's ``conftest.py``.
"""

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.dependencies.database.models import Dataset, Metric, Run
from DashAI.back.job.dataset_job import DatasetJob
from DashAI.back.job.model_job import ModelJob

GOLDEN_PATH = Path(__file__).with_name("forecasting_core_net_golden.json")
RECORDING = os.environ.get("DASHAI_RECORD_FORECASTING_CORE_NET") == "1"

HORIZON = 6

# --------------------------------------------------------------------------- #
# The golden values
# --------------------------------------------------------------------------- #

_recorded: dict = {}


@pytest.fixture(scope="module", name="golden", autouse=True)
def fixture_golden():
    if RECORDING:
        yield None
        existing = (
            json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
            if GOLDEN_PATH.exists()
            else {}
        )
        existing.update(_recorded)
        GOLDEN_PATH.write_text(
            json.dumps(existing, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        yield json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _plain(value):
    """A JSON-comparable copy: numpy scalars and arrays, tuples and frames."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return _plain(value.tolist())
    if isinstance(value, pd.DataFrame):
        return _plain(value.to_dict(orient="list"))
    if isinstance(value, pd.Series):
        return _plain(value.tolist())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _same(value, expected) -> bool:
    """Equal, floats to a relative 1e-9 and everything else exactly."""
    if isinstance(value, float) or isinstance(expected, float):
        numbers = (int, float)
        return (
            isinstance(value, numbers)
            and isinstance(expected, numbers)
            and not isinstance(value, bool)
            and not isinstance(expected, bool)
            and math.isclose(value, expected, rel_tol=1e-9, abs_tol=1e-9)
        )
    if isinstance(value, dict) and isinstance(expected, dict):
        return value.keys() == expected.keys() and all(
            _same(value[k], expected[k]) for k in value
        )
    if isinstance(value, list) and isinstance(expected, list):
        return len(value) == len(expected) and all(map(_same, value, expected))
    return value == expected


def _pin(golden, key: str, value) -> None:
    value = json.loads(json.dumps(_plain(value)))
    if RECORDING:
        _recorded[key] = value
        return
    assert key in golden, f"{key} was never recorded"
    if not _same(value, golden[key]):
        assert value == golden[key], key


# --------------------------------------------------------------------------- #
# The series
# --------------------------------------------------------------------------- #


def _monthly() -> pd.DataFrame:
    """Four years of a trending, seasonal monthly series, with fixed noise."""
    steps = np.arange(48)
    noise = np.random.RandomState(0).normal(0.0, 1.5, size=48)
    values = 100.0 + 0.8 * steps + 10.0 * np.sin(2 * np.pi * steps / 12) + noise
    dates = pd.date_range("2020-01-01", periods=48, freq="MS")
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": values})


def _daily() -> pd.DataFrame:
    """Eight weeks of a trending daily series with a weekly season."""
    steps = np.arange(56)
    noise = np.random.RandomState(1).normal(0.0, 0.5, size=56)
    values = 50.0 + 0.2 * steps + 5.0 * np.sin(2 * np.pi * steps / 7) + noise
    dates = pd.date_range("2024-01-01", periods=56, freq="D")
    return pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "sales": values})


SERIES = {"monthly": _monthly, "daily": _daily}


def _dataset(frame: pd.DataFrame, value_type=("Float", "float64")):
    value, dtype = value_type
    schema = {
        "date": {"type": "Date", "dtype": "%Y-%m-%d"},
        "sales": {"type": value, "dtype": dtype},
    }
    schema = {name: schema[name] for name in frame.columns}
    return transform_dataset_with_schema(to_dashai_dataset(frame), schema)


# --------------------------------------------------------------------------- #
# The one helper that knows a model's API
# --------------------------------------------------------------------------- #


def _forecast(model_class, params: dict, frame: pd.DataFrame, horizon: int):
    """Fit on the whole series and forecast ``horizon`` steps past its end."""
    dataset = _dataset(frame)
    model = model_class(**params)
    model.train(dataset.select_columns(["date"]), dataset.select_columns(["sales"]))

    last = pd.Timestamp(frame["date"].iloc[-1])
    step = pd.Timestamp(frame["date"].iloc[1]) - pd.Timestamp(frame["date"].iloc[0])
    freq = "MS" if step.days > 27 else "D"
    future = pd.date_range(last, periods=horizon + 1, freq=freq)[1:]
    future_x = _dataset(pd.DataFrame({"date": future.strftime("%Y-%m-%d")}))
    return np.asarray(model.predict(future_x), dtype=float)


def _model_classes():
    from DashAI.back.models.forecasting.arima import ARIMA
    from DashAI.back.models.forecasting.exponential_smoothing import (
        ExponentialSmoothing,
    )
    from DashAI.back.models.forecasting.naive import NaiveForecaster
    from DashAI.back.models.forecasting.seasonal_naive import SeasonalNaiveForecaster

    return {
        "naive": NaiveForecaster,
        "seasonal_naive": SeasonalNaiveForecaster,
        "arima": ARIMA,
        "ets": ExponentialSmoothing,
    }


MODEL_CASES = {
    "monthly/naive": ("naive", {}),
    "monthly/seasonal_naive_12": ("seasonal_naive", {"season_length": 12}),
    "monthly/arima_110": ("arima", {"p": 1, "d": 1, "q": 0}),
    "monthly/arima_211": ("arima", {"p": 2, "d": 1, "q": 1}),
    "monthly/ets_level": ("ets", {}),
    "monthly/ets_add_add_12": (
        "ets",
        {"trend": "add", "seasonal": "add", "season_length": 12},
    ),
    "daily/naive": ("naive", {}),
    "daily/seasonal_naive_7": ("seasonal_naive", {"season_length": 7}),
    "daily/arima_110": ("arima", {"p": 1, "d": 1, "q": 0}),
    "daily/ets_add_add_7": (
        "ets",
        {"trend": "add", "seasonal": "add", "season_length": 7},
    ),
}


@pytest.mark.parametrize("key", list(MODEL_CASES))
def test_a_model_forecasts_a_clean_series_the_same(golden, key):
    series, _ = key.split("/")
    model, params = MODEL_CASES[key]
    forecast = _forecast(_model_classes()[model], params, SERIES[series](), HORIZON)
    _pin(golden, f"forecast/{key}", forecast)


# --------------------------------------------------------------------------- #
# The notebook's series pieces
# --------------------------------------------------------------------------- #


class _Explorer:
    """Stand-in for the Explorer database record the explorers receive."""

    def __init__(self, columns):
        self.id = 1
        self.name = ""
        self.columns = [{"columnName": col} for col in columns]


def _traces(figure) -> list:
    return [
        {"name": trace.name, "y": [_plain(v) for v in trace.y]} for trace in figure.data
    ]


def _irregular_daily() -> pd.DataFrame:
    """Daily readings with a missing week and two readings on one day."""
    frame = _daily().iloc[:40]
    frame = frame.drop(index=range(10, 17))
    extra = frame.iloc[[3]].assign(sales=frame["sales"].iloc[3] + 4.0)
    return pd.concat([frame, extra]).reset_index(drop=True)


RESAMPLER_CASES = {
    "month_mean": {"frequency": "month", "aggregation": "mean"},
    "week_sum_forward": {"frequency": "week", "aggregation": "sum", "fill": "forward"},
    "day_mean_interpolate": {
        "frequency": "day",
        "aggregation": "mean",
        "fill": "interpolate",
    },
}


@pytest.mark.parametrize("key", list(RESAMPLER_CASES))
def test_the_resampler_puts_a_series_on_the_same_grid(golden, key):
    from DashAI.back.converters.simple_converters.time_resampler import (
        TimeResamplerConverter,
    )

    dataset = _dataset(_irregular_daily())
    converter = TimeResamplerConverter(**RESAMPLER_CASES[key])
    result = converter.fit(dataset).transform(dataset)

    _pin(golden, f"resampler/{key}", result.to_pandas())


DATE_FEATURE_CASES = {
    "defaults": {},
    "every_feature_cyclical": {
        "year": True,
        "month": True,
        "day": True,
        "weekday": True,
        "quarter": True,
        "week_of_year": True,
        "day_of_year": True,
        "cyclical": True,
    },
}


@pytest.mark.parametrize("key", list(DATE_FEATURE_CASES))
def test_the_calendar_features_are_the_same(golden, key):
    from DashAI.back.converters.simple_converters.date_features import (
        DateFeaturesConverter,
    )

    dataset = _dataset(_daily().iloc[:20]).select_columns(["date"])
    converter = DateFeaturesConverter(**DATE_FEATURE_CASES[key])
    result = converter.fit(dataset).transform(dataset)

    _pin(golden, f"date_features/{key}", result.to_pandas())


def test_the_window_converter_builds_the_same_table(golden):
    from DashAI.back.converters.simple_converters.time_series_window import (
        TimeSeriesWindowConverter,
    )

    dataset = _dataset(_monthly())
    x, y = dataset.select_columns(["date"]), dataset.select_columns(["sales"])
    converter = TimeSeriesWindowConverter(window_size=3)
    result = converter.fit(x, y).transform(x, y)

    _pin(golden, "window/size_3", result.to_pandas())


DECOMPOSITION_CASES = {
    "stl_additive": {"method": "stl", "period": 0, "model": "additive"},
    "moving_average_additive": {
        "method": "moving_average",
        "period": 12,
        "model": "additive",
    },
}


@pytest.mark.parametrize("key", list(DECOMPOSITION_CASES))
def test_the_decomposition_splits_the_series_the_same(golden, key):
    from DashAI.back.exploration.explorers.seasonal_decomposition import (
        SeasonalDecompositionExplorer,
    )

    explorer = SeasonalDecompositionExplorer(**DECOMPOSITION_CASES[key])
    figure = explorer.launch_exploration(
        _dataset(_monthly()), _Explorer(["date", "sales"])
    )

    _pin(golden, f"decomposition/{key}", _traces(figure))


def test_the_correlogram_is_the_same(golden):
    from DashAI.back.exploration.explorers.autocorrelation_plot import (
        AutocorrelationExplorer,
    )

    explorer = AutocorrelationExplorer(n_lags=12, function="both", confidence=0.95)
    figure = explorer.launch_exploration(
        _dataset(_monthly()), _Explorer(["date", "sales"])
    )

    _pin(golden, "correlogram/both_12", _traces(figure))


# --------------------------------------------------------------------------- #
# The windowed route through a regression session
# --------------------------------------------------------------------------- #

WINDOW_FEATURES = ["lag_3", "lag_2", "lag_1"]
WINDOW_METRICS = ["MAE", "RMSE", "R2"]
SEQUENTIAL_HOLDOUT = {
    "splitter_name": "HoldoutSplitter",
    "splitType": "random",
    "train": 0.6,
    "test": 0.2,
    "validation": 0.2,
    "shuffle": False,
    "stratify": False,
    "seed": 0,
}


def _get(client: TestClient, model, row_id):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        row = db.get(model, row_id)
        db.expunge(row)
        return row


def _windowed_csv(directory: Path) -> Path:
    from DashAI.back.converters.simple_converters.time_series_window import (
        TimeSeriesWindowConverter,
    )

    dataset = _dataset(_monthly())
    x, y = dataset.select_columns(["date"]), dataset.select_columns(["sales"])
    table = TimeSeriesWindowConverter(window_size=3).fit(x, y).transform(x, y)
    path = directory / "windowed.csv"
    table.to_pandas().to_csv(path, index=False)
    return path


def _create_dataset(client: TestClient, path: Path, name: str) -> int:
    session_factory = client.app.container["session_factory"]
    columns = [*WINDOW_FEATURES, "target"]
    with session_factory() as db:
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
                        column: {"type": "Float", "dtype": "float64"}
                        for column in columns
                    },
                },
                "file_path": path,
            },
            db=db,
        ).run()
        db.refresh(entry)
        return entry.id


@pytest.fixture(scope="module", name="windowed_run")
def fixture_windowed_run(client: TestClient, tmp_path_factory) -> dict:
    directory = tmp_path_factory.mktemp("windowed")
    dataset_id = _create_dataset(
        client, _windowed_csv(directory), "forecasting-core-net-windowed"
    )
    response = client.post(
        "/api/v1/model-session/",
        json={
            "dataset_id": dataset_id,
            "task_name": "RegressionTask",
            "name": "forecasting-core-net-windowed",
            "column_roles": {
                "features": [{"kind": "raw", "name": c} for c in WINDOW_FEATURES],
                "target": [{"kind": "raw", "name": "target"}],
            },
            "train_metrics": WINDOW_METRICS,
            "validation_metrics": WINDOW_METRICS,
            "test_metrics": WINDOW_METRICS,
            "evaluation_strategy": "HoldoutEvaluationStrategy",
            "splits": json.dumps(SEQUENTIAL_HOLDOUT),
            "preprocessing": [],
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["id"]

    response = client.post(
        "/api/v1/run/",
        json={
            "model_session_id": session_id,
            "model_name": "LinearRegression",
            "name": "windowed linear regression",
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
    return {"run_id": run_id, "csv": directory / "windowed.csv"}


def _metric_rows(client: TestClient, run_id: int) -> list:
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        rows = db.query(Metric).filter(Metric.run_id == run_id).all()
        return sorted(
            ([row.split.value, row.level.value, row.name, row.value] for row in rows),
            key=lambda r: [str(x) for x in r[:3]],
        )


def test_the_windowed_run_partitions_the_same_rows(client, windowed_run, golden):
    split_indexes = json.loads(_get(client, Run, windowed_run["run_id"]).split_indexes)
    _pin(golden, "windowed/split_indexes", split_indexes)


def test_the_windowed_run_scores_the_same(client, windowed_run, golden):
    _pin(golden, "windowed/metrics", _metric_rows(client, windowed_run["run_id"]))


def test_the_windowed_run_scores_what_sklearn_scores(client, windowed_run):
    """The stored metrics are sklearn's, on the rows the run says it used.

    Independent of the golden file: it would catch a metric that drifted on
    the base too.
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

    run_id = windowed_run["run_id"]
    split_indexes = json.loads(_get(client, Run, run_id).split_indexes)
    table = pd.read_csv(windowed_run["csv"])
    x, y = table[WINDOW_FEATURES].to_numpy(), table["target"].to_numpy()
    train = split_indexes["train_indexes"]
    test = split_indexes["test_indexes"]
    predicted = LinearRegression().fit(x[train], y[train]).predict(x[test])

    stored = {
        name: value
        for split, level, name, value in _metric_rows(client, run_id)
        if split == "test" and level == "last"
    }
    assert stored["MAE"] == pytest.approx(mean_absolute_error(y[test], predicted))
    assert stored["RMSE"] == pytest.approx(root_mean_squared_error(y[test], predicted))
    assert stored["R2"] == pytest.approx(r2_score(y[test], predicted))
