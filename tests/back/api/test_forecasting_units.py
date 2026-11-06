"""Contract tests of the backtest units, with the context built by hand.

The end to end cases (``test_forecasting_acceptance.py``) always wire the
units the way ``ModelJob`` does; these feed each unit what its ``REQUIRES``
says and nothing else, and check exactly what it publishes (ATOMIZING §6).

Lives under ``tests/back/api`` to reuse the ``client`` fixture, whose
container holds the registry the units resolve components from.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.tasks.time_grid import TimeGrid
from DashAI.back.units.backtest_forecaster_unit import BacktestForecasterUnit
from DashAI.back.units.build_forecaster_unit import BuildForecasterUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.fit_final_forecaster_unit import FitFinalForecasterUnit
from DashAI.back.units.forecast_scope import season_length_for
from DashAI.back.units.prepare_series_unit import PrepareSeriesUnit
from DashAI.back.units.score_forecasts_unit import ScoreForecastsUnit

TASK = "SingleSeriesForecastingTask"
SERIES = np.arange(1.0, 25.0)
GRID = TimeGrid(
    freq="MS",
    first=pd.Timestamp("2020-01-01"),
    last=pd.Timestamp("2021-12-01"),
    n_steps=24,
)
CUTS = {"horizon": 3, "validation_origins": [15, 18], "test_origin": 21, "n_steps": 24}
NO_SEARCH = {"component": "", "params": {}}


@pytest.fixture(autouse=True, name="registry")
def _the_app_registry(client):
    """The units resolve components through the app's container."""
    return client.app.container["component_registry"]


def _dataset(dates, values):
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame({"date": dates, "v": values})),
        {
            "date": {"type": "Date", "dtype": "%Y-%m-%d"},
            "v": {"type": "Float", "dtype": "float64"},
        },
    )


def _context(**values):
    ctx = ExecutionContext()
    for key, value in values.items():
        if key in ("grid", "split_indexes", "task_name", "model_parameters"):
            ctx.put_ref(key, value)
        else:
            ctx.put(key, value)
    return ctx


# --- PrepareSeriesUnit -------------------------------------------------------


def _prepare(splitter=None):
    return PrepareSeriesUnit(
        task_name=TASK,
        input_columns=["date"],
        output_columns=["v"],
        splitter=splitter
        or {
            "component": "RollingOriginSplitter",
            "params": {"horizon": 3, "n_origins": 2},
        },
    )


def test_the_series_comes_out_in_time_order_with_its_grid_and_cuts():
    dates = pd.date_range("2020-01-01", periods=24, freq="MS").strftime("%Y-%m-%d")
    shuffled = np.random.RandomState(0).permutation(24)
    ctx = _context(
        dataset=_dataset(list(dates[shuffled]), list(SERIES[shuffled])), dataset_id=1
    )

    _prepare()(ctx)

    assert list(ctx.require("series")) == list(SERIES)
    assert ctx.require("grid") == GRID.to_ref()
    assert ctx.require("split_indexes") == CUTS
    assert ctx.require("task_name") == TASK
    # The rows too, in the same order, for the unit that reads the exogenous
    # variables one step per row.
    rows = ctx.require("dataset").to_pandas()
    assert list(rows["date"]) == list(dates)
    assert list(rows["v"]) == list(SERIES)


def test_a_series_off_its_grid_is_a_job_error_with_the_tasks_message():
    dates = ["2020-01-01", "2020-02-01", "2020-04-01", "2020-05-01", "2020-06-01"]
    ctx = _context(dataset=_dataset(dates, [1.0, 2.0, 3.0, 4.0, 5.0]), dataset_id=7)

    with pytest.raises(JobError, match="dataset 7 cannot be forecast.*TimeResampler"):
        _prepare()(ctx)


def test_a_series_too_short_for_the_cuts_is_a_job_error():
    dates = pd.date_range("2020-01-01", periods=6, freq="MS").strftime("%Y-%m-%d")
    ctx = _context(dataset=_dataset(list(dates), list(range(6))), dataset_id=1)

    with pytest.raises(JobError, match="needs a series of at least 10 steps"):
        _prepare()(ctx)


# --- BuildForecasterUnit -----------------------------------------------------


@pytest.mark.parametrize(
    ("freq", "season"),
    [
        ("MS", 12),
        ("ME", 12),
        ("D", 7),
        ("h", 24),
        ("QS-JAN", 4),
        ("W-SUN", 52),
        ("YS", 1),
    ],
)
def test_the_season_follows_the_frequency(freq, season):
    assert season_length_for(freq) == season


def _build(params):
    ctx = _context(task_name=TASK, grid=GRID.to_ref())
    BuildForecasterUnit(
        model={"component": "SeasonalNaiveForecaster", "params": params}, run_id=None
    )(ctx)
    return ctx


def test_a_season_left_out_comes_from_the_grid():
    ctx = _build({})

    assert ctx.require("model").season_length == 12
    assert ctx.require("model_parameters") == {"season_length": 12}


def test_a_season_given_is_kept_even_if_it_is_one():
    ctx = _build({"season_length": 1})

    assert ctx.require("model").season_length == 1


# --- BacktestForecasterUnit --------------------------------------------------


#: A planned promotion every third month, and what it adds to the series.
PROMO = np.array([1.0 if i % 3 == 1 else 0.0 for i in range(24)]).reshape(-1, 1)
WITH_PROMO = SERIES + 6.0 * PROMO[:, 0] + np.cos(np.arange(24.0))
ARIMA_100 = {"p": 1, "d": 0, "q": 0}


def _cut(name, values=None):
    if values is None:
        return {"name": name, "columns": [], "values": np.empty((24, 0))}
    return {"name": name, "columns": ["promo"], "values": values}


def _exogenous(values=None):
    """What ``ApplyCutPreprocessingUnit`` publishes: the same raw cut each time."""
    return {
        "declared": values is not None,
        "validation": [_cut("origin_0", values), _cut("origin_1", values)],
        "test": _cut("test", values),
        "final": _cut("final", values),
    }


def _backtested(
    model="NaiveForecaster",
    params=None,
    series=SERIES,
    exogenous=None,
    optimizer=None,
    published=None,
):
    ctx = _context(task_name=TASK, grid=GRID.to_ref())
    BuildForecasterUnit(
        model={"component": model, "params": params or {}}, run_id=None
    )(ctx)
    ctx.put("series", series)
    ctx.put_ref("split_indexes", CUTS)
    ctx.put("exogenous", published or _exogenous(exogenous))
    BacktestForecasterUnit(
        optimizer=optimizer or NO_SEARCH,
        goal_metric="MAE" if optimizer else "",
        run_id=None,
        artifact_prefix="test",
    )(ctx)
    return ctx


def _by_hand(origin, x=None, params=ARIMA_100):
    from DashAI.back.models.forecasting.arima import ARIMA

    model = ARIMA(**params).fit(WITH_PROMO[:origin], None if x is None else x[:origin])
    future = None if x is None else x[origin : origin + 3]
    return list(model.predict(3, x_future=future).point)


def test_a_model_that_takes_them_forecasts_every_origin_with_its_cut():
    origins = _backtested("ARIMA", ARIMA_100, WITH_PROMO, PROMO).require("forecasts")[
        "origins"
    ]

    for record in origins:
        expected = _by_hand(record["origin_step"], PROMO)
        assert record["forecast"] == pytest.approx(expected, rel=1e-9)


def test_switched_off_the_model_forecasts_without_them():
    params = {**ARIMA_100, "use_exogenous": False}
    origins = _backtested("ARIMA", params, WITH_PROMO, PROMO).require("forecasts")[
        "origins"
    ]

    for record in origins:
        assert record["forecast"] == pytest.approx(
            _by_hand(record["origin_step"]), rel=1e-9
        )


def test_a_model_that_takes_none_is_never_handed_them():
    # Naive refuses an x; the unit leaves it out rather than fail.
    origins = _backtested(exogenous=PROMO).require("forecasts")["origins"]

    assert origins[0]["forecast"] == [15.0] * 3


def test_a_cut_left_without_columns_is_refused_when_the_run_reads_them():
    # The session declares the role, so the run reads its exogenous variables;
    # a cut whose preprocessing resolved none is not trained without them.
    published = _exogenous(PROMO)
    published["validation"][0] = _cut("origin_0")

    with pytest.raises(JobError, match="origin_0"):
        _backtested("ARIMA", ARIMA_100, WITH_PROMO, published=published)


def test_a_cut_left_without_columns_is_fine_for_a_model_that_reads_none():
    published = _exogenous(PROMO)
    published["validation"][0] = _cut("origin_0")

    origins = _backtested(published=published).require("forecasts")["origins"]

    assert origins[0]["forecast"] == [15.0] * 3


def test_a_search_trial_forecasts_with_the_exogenous_columns(monkeypatch):
    from DashAI.back.units import backtest_forecaster_unit

    handed = []
    original = backtest_forecaster_unit.forecast_origin

    def recording(*args, **kwargs):
        handed.append(kwargs.get("x"))
        return original(*args, **kwargs)

    monkeypatch.setattr(backtest_forecaster_unit, "forecast_origin", recording)
    searched = {
        "p": {"optimize": True, "fixed_value": 1, "lower_bound": 1, "upper_bound": 1},
        "d": 0,
        "q": 0,
    }

    _backtested(
        "ARIMA",
        searched,
        WITH_PROMO,
        PROMO,
        optimizer={
            "component": "OptunaOptimizer",
            "params": {"n_trials": 1, "sampler": "TPESampler", "pruner": "None"},
        },
    )

    # The trial's two validation origins, then the backtest's three.
    assert len(handed) == 5
    assert all(x is not None and x.shape == (24, 1) for x in handed)


def test_the_model_published_is_the_factorys_own():
    # ATOMIZING 5.7: the backtest searches on ``model`` and writes the values
    # it finds back through ``factory``; a copy in between would search one
    # object and report the parameters of another.
    ctx = _context(task_name=TASK, grid=GRID.to_ref())

    BuildForecasterUnit(
        model={"component": "NaiveForecaster", "params": {}}, run_id=None
    )(ctx)

    assert ctx.require("model") is ctx.require("factory").model


def test_every_origin_is_forecast_from_the_steps_before_it():
    forecasts = _backtested().require("forecasts")

    origins = forecasts["origins"]
    assert [(o["partition"], o["index"], o["origin_step"]) for o in origins] == [
        ("validation", 0, 15),
        ("validation", 1, 18),
        ("test", 0, 21),
    ]
    # Naive forecasts the last value before its origin.
    assert [o["forecast"] for o in origins] == [[15.0] * 3, [18.0] * 3, [21.0] * 3]
    assert origins[-1]["actual"] == [22.0, 23.0, 24.0]
    assert origins[-1]["dates"] == [
        "2021-10-01T00:00:00",
        "2021-11-01T00:00:00",
        "2021-12-01T00:00:00",
    ]
    assert forecasts["levels"] == [80, 95]
    assert set(origins[0]["lower"]) == {"80", "95"}
    assert forecasts["freq"] == "MS"
    assert forecasts["horizon"] == 3


def test_without_a_search_the_best_parameters_are_the_ones_given():
    ctx = _backtested("SeasonalNaiveForecaster", {"season_length": 3})

    assert ctx.require("best_parameters") == {"season_length": 3}
    assert ctx.require("plot_paths") == []
    assert ctx.require("forecasts")["season_length"] == 3


# --- ScoreForecastsUnit ------------------------------------------------------


def _scored(validation_metrics, test_metrics, series=SERIES):
    ctx = _backtested(series=series)
    ScoreForecastsUnit(
        validation_metrics=validation_metrics, test_metrics=test_metrics
    )(ctx)
    return ctx.require("forecast_metrics")


def test_each_origin_is_scored_and_summarised():
    rows = _scored(["MAE"], ["MAE"])

    by_kind = {(r["split"], r["level"], r["fold_index"]): r for r in rows}
    # Naive misses each window by 1, 2 and 3: MAE 2 on every origin.
    assert by_kind[("VALIDATION", "FOLD", 0)]["value"] == pytest.approx(2.0)
    assert by_kind[("VALIDATION", "FOLD", 1)]["value"] == pytest.approx(2.0)
    assert by_kind[("VALIDATION", "LAST", None)]["value"] == pytest.approx(2.0)
    assert by_kind[("VALIDATION", "LAST", None)]["std_value"] == pytest.approx(0.0)
    assert by_kind[("TEST", "LAST", None)]["value"] == pytest.approx(2.0)


def test_a_metric_with_no_value_on_one_origin_has_no_summary():
    series = SERIES.copy()
    series[19] = 0.0  # inside the second validation window, 18 to 20

    rows = _scored(["MAPE"], ["MAPE"], series)

    folds = sorted(
        (r for r in rows if r["level"] == "FOLD"), key=lambda r: r["fold_index"]
    )
    assert folds[0]["value"] is not None
    assert folds[1]["value"] is None
    assert "zero" in folds[1]["unavailable_reason"]
    summary = next(
        r for r in rows if r["split"] == "VALIDATION" and r["level"] == "LAST"
    )
    assert summary["value"] is None
    assert summary["unavailable_reason"] == folds[1]["unavailable_reason"]
    test = next(r for r in rows if r["split"] == "TEST")
    assert test["value"] is not None


def test_an_unavailable_reason_names_the_dates_that_leave_it_undefined():
    series = SERIES.copy()
    series[19] = 0.0  # 2021-08-01, inside the second validation window

    rows = _scored(["MAPE"], [], series)

    fold = next(r for r in rows if r["level"] == "FOLD" and r["fold_index"] == 1)
    assert "the actual value is zero on 2021-08-01." in fold["unavailable_reason"]


def test_coverage_is_scored_on_the_intervals():
    rows = _scored(["IntervalCoverage"], [])

    assert all(0.0 <= r["value"] <= 1.0 for r in rows)


# --- FitFinalForecasterUnit --------------------------------------------------


def test_the_kept_model_is_fresh_and_has_seen_the_whole_series():
    ctx = _backtested()
    backtested = ctx.require("model")

    FitFinalForecasterUnit()(ctx)

    kept = ctx.require("model")
    assert kept is not backtested
    assert kept.predict(1).point[0] == pytest.approx(24.0)
    assert kept.time_grid == GRID.to_ref()


def test_the_kept_model_is_fitted_on_the_final_cut():
    ctx = _backtested("ARIMA", ARIMA_100, WITH_PROMO, PROMO)

    FitFinalForecasterUnit()(ctx)

    kept = ctx.require("model")
    future = np.array([[1.0], [0.0], [0.0]])
    from DashAI.back.models.forecasting.arima import ARIMA

    by_hand = ARIMA(**ARIMA_100).fit(WITH_PROMO, PROMO).predict(3, x_future=future)
    assert list(kept.predict(3, x_future=future).point) == pytest.approx(
        list(by_hand.point), rel=1e-9
    )


def test_a_final_cut_left_without_columns_is_refused_when_the_run_reads_them():
    published = _exogenous(PROMO)
    published["final"] = _cut("final")
    ctx = _backtested("ARIMA", ARIMA_100, WITH_PROMO, published=published)

    with pytest.raises(JobError, match="final"):
        FitFinalForecasterUnit()(ctx)


# --- ModelJob._exogenous_record ----------------------------------------------


def test_the_run_records_the_decision_its_session_and_model_make(registry):
    """What the run records comes from the session's role, the model and its
    parameters, the same answer the units and the session's mark give: not
    from the columns one cut happened to resolve."""
    from types import SimpleNamespace

    from DashAI.back.job.model_job import ModelJob

    ctx = ExecutionContext()
    ctx.put("exogenous", {**_exogenous(PROMO), "final": _cut("final")})
    ctx.put(
        "dataset",
        transform_dataset_with_schema(
            to_dashai_dataset(pd.DataFrame({"promo": PROMO[:, 0]})),
            {"promo": {"type": "Float", "dtype": "float64"}},
        ),
    )

    record = ModelJob._exogenous_record(
        SimpleNamespace(model_name="NaiveForecaster", parameters={}),
        SimpleNamespace(preprocessing=None),
        SimpleNamespace(
            config={"exogenous_column_refs": [{"kind": "raw", "name": "promo"}]}
        ),
        ctx,
        registry,
    )

    assert record["used"] is False
    assert record["reason"]["key"] == "modelTakesNoExogenous"
    assert record["columns"] == [{"name": "promo", "type": "Float"}]


# --- SaveForecastsUnit -------------------------------------------------------


def test_the_forecasts_are_written_where_the_endpoint_reads_them(client):
    import json

    from DashAI.back.units.forecast_scope import forecasts_file
    from DashAI.back.units.save_forecasts_unit import SaveForecastsUnit

    ctx = _backtested()

    SaveForecastsUnit(artifact_prefix="unit-test")(ctx)

    path = forecasts_file(client.app.container["config"]["RUNS_PATH"], "unit-test")
    assert ctx.require("forecasts_path") == str(path)
    assert json.loads(path.read_text(encoding="utf-8")) == ctx.require("forecasts")
    assert not path.with_suffix(".json.partial").exists()
    path.unlink()


def test_a_forecast_that_is_not_a_number_is_not_written(client):
    # NaN is not JSON: the file would hold a bare NaN that the frontend
    # cannot parse. The origins carry None where a value is not finite, so a
    # NaN here came from somewhere else, and is an error to say, not to save.
    from DashAI.back.units.forecast_scope import forecasts_file
    from DashAI.back.units.save_forecasts_unit import SaveForecastsUnit

    ctx = _backtested()
    forecasts = ctx.require("forecasts")
    forecasts["origins"][0]["forecast"][0] = float("nan")
    ctx.put_ref("forecasts", forecasts)

    with pytest.raises(JobError, match="not a number"):
        SaveForecastsUnit(artifact_prefix="nan-test")(ctx)

    path = forecasts_file(client.app.container["config"]["RUNS_PATH"], "nan-test")
    assert not path.exists()
    assert not path.with_suffix(".json.partial").exists()


@pytest.mark.parametrize("prefix", ["../outside", "", None])
def test_a_prefix_that_leaves_the_runs_directory_is_refused(prefix):
    from DashAI.back.units.save_forecasts_unit import SaveForecastsUnit

    with pytest.raises(JobError, match="artifact prefix"):
        SaveForecastsUnit(artifact_prefix=prefix)(_context(forecasts={}))


# --- ForecastHorizonUnit -----------------------------------------------------


def test_the_horizon_is_dated_after_the_kept_models_last_step():
    from DashAI.back.units.forecast_horizon_unit import ForecastHorizonUnit

    ctx = _backtested()
    FitFinalForecasterUnit()(ctx)
    ctx.put_ref(
        "train_dataset_types",
        {"date": {"type": "Date", "dtype": "date32", "format": "%Y-%m-%d"}},
    )

    ForecastHorizonUnit(horizon=2, input_columns=["date"])(ctx)

    assert list(ctx.require("dataset").to_pandas()["date"]) == [
        "2022-01-01",
        "2022-02-01",
    ]
    assert list(ctx.require("y_pred")) == pytest.approx([24.0, 24.0])


def test_a_model_without_a_grid_cannot_date_its_forecast():
    from DashAI.back.models.forecasting.naive import NaiveForecaster
    from DashAI.back.units.forecast_horizon_unit import ForecastHorizonUnit

    ctx = _context(model=NaiveForecaster().fit(SERIES))
    ctx.put_ref("train_dataset_types", {})

    with pytest.raises(JobError, match="no grid to name the dates"):
        ForecastHorizonUnit(horizon=2, input_columns=["date"])(ctx)
