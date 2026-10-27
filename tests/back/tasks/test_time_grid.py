"""A series has to sit on a regular grid before a forecaster sees it.

The helpers refuse, with a message that says what failed and where, and never
correct anything: filling a gap or dropping a duplicate is the user's call, in
the notebook.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.tasks.single_series_forecasting_task import (
    SingleSeriesForecastingTask,
)
from DashAI.back.tasks.time_grid import (
    TimeGrid,
    infer_grid_frequency,
    time_order,
    validate_grid,
)


def _monthly(n=12):
    return pd.Series(pd.date_range("2020-01-01", periods=n, freq="MS"))


def _values(n):
    return pd.Series(np.arange(n, dtype=float))


# --- the frequency -----------------------------------------------------------


@pytest.mark.parametrize("freq", ["MS", "D", "h", "W-SUN", "QS-JAN", "YS"])
def test_the_frequency_of_a_regular_series_lays_out_its_dates(freq):
    # Compared by the grid it lays out, not by name: pandas may name the same
    # quarterly grid QS-JAN or QS-OCT.
    index = pd.date_range("2021-01-03", periods=10, freq=freq)

    alias = infer_grid_frequency(index)

    assert pd.date_range(index[0], periods=10, freq=alias).equals(index)


def test_a_series_with_a_gap_still_has_the_frequency_of_its_stretches():
    index = pd.DatetimeIndex(_monthly(12).drop(index=[5, 6]))

    assert infer_grid_frequency(index) == "MS"


def test_a_short_daily_series_with_a_gap_falls_back_to_its_smallest_step():
    # No three consecutive dates are regular, but a day is a fixed step.
    index = pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-04", "2020-01-05"])

    assert infer_grid_frequency(index) == "D"


def test_dates_that_drift_off_any_grid_have_no_frequency():
    index = pd.DatetimeIndex(
        ["2020-01-01", "2020-01-05", "2020-01-12", "2020-01-14", "2020-02-20"]
    )

    assert infer_grid_frequency(index) is None


def test_two_dates_are_too_few_to_name_a_frequency():
    assert infer_grid_frequency(pd.DatetimeIndex(["2020-01-01", "2020-02-01"])) is None


# --- the order ---------------------------------------------------------------


def test_the_order_is_stable_and_puts_empty_dates_last():
    dates = pd.Series(
        pd.to_datetime(["2020-03-01", None, "2020-01-01", "2020-03-01", "2020-02-01"])
    )

    assert time_order(dates) == [2, 4, 0, 3, 1]


# --- what is refused ---------------------------------------------------------


def test_a_clean_series_gives_its_grid():
    grid = validate_grid(_monthly(12), _values(12))

    assert grid == TimeGrid(
        freq="MS",
        first=pd.Timestamp("2020-01-01"),
        last=pd.Timestamp("2020-12-01"),
        n_steps=12,
    )


def test_an_empty_date_is_refused_with_a_count():
    dates = _monthly(6)
    dates[5] = pd.NaT

    with pytest.raises(ValueError, match=r"1 row\(s\) with no date"):
        validate_grid(dates, _values(6))


def test_a_repeated_date_is_refused_naming_it():
    dates = pd.concat([_monthly(6), _monthly(6).iloc[[2]]]).sort_values()

    with pytest.raises(ValueError, match="repeats 1 date.*2020-03-01"):
        validate_grid(dates, _values(7))


def test_dates_with_no_frequency_are_refused():
    dates = pd.Series(
        pd.to_datetime(["2020-01-01", "2020-01-05", "2020-01-12", "2020-01-14"])
    )

    with pytest.raises(ValueError, match="do not follow a regular frequency"):
        validate_grid(dates, _values(4))


def test_a_missing_period_is_refused_naming_it():
    dates = _monthly(12).drop(index=[5, 6]).reset_index(drop=True)

    with pytest.raises(
        ValueError, match=r"misses 2 period\(s\).*2020-06-01, 2020-07-01"
    ):
        validate_grid(dates, _values(10))


def test_an_empty_value_is_refused_naming_its_date():
    values = _values(12)
    values[3] = np.nan

    with pytest.raises(ValueError, match=r"1 empty value\(s\), at 2020-04-01"):
        validate_grid(_monthly(12), values)


def test_a_long_list_of_dates_is_summarised():
    dates = pd.Series(pd.date_range("2020-01-01", periods=40, freq="D"))
    dates = dates[dates.dt.day % 3 != 0].reset_index(drop=True)

    with pytest.raises(ValueError, match="and [0-9]+ more"):
        validate_grid(dates, _values(len(dates)))


@pytest.mark.parametrize(
    "case", ["empty date", "repeated", "no frequency", "missing", "empty value"]
)
def test_every_refusal_says_how_to_fix_it(case):
    dates, values = _monthly(12), _values(12)
    if case == "empty date":
        dates[0] = pd.NaT
    elif case == "repeated":
        dates[1] = dates[0]
    elif case == "no frequency":
        dates = pd.Series(pd.to_datetime(["2020-01-01", "2020-01-05", "2020-01-12"]))
        values = _values(3)
    elif case == "missing":
        dates, values = dates.drop(index=[4]).reset_index(drop=True), _values(11)
    else:
        values[2] = np.nan

    with pytest.raises(ValueError, match="TimeResampler"):
        validate_grid(dates, values)


# --- the grid ----------------------------------------------------------------


def test_the_grid_names_the_dates_of_any_steps():
    grid = validate_grid(_monthly(12), _values(12))

    assert list(grid.dates(10, 4)) == list(
        pd.to_datetime(["2020-11-01", "2020-12-01", "2021-01-01", "2021-02-01"])
    )


def test_the_grid_survives_a_round_trip_through_json():
    grid = validate_grid(_monthly(12), _values(12))

    assert TimeGrid.from_ref(grid.to_ref()) == grid


# --- the task ----------------------------------------------------------------


def _dataset(dates, values):
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame({"date": dates, "v": values})),
        {
            "date": {"type": "Date", "dtype": "%Y-%m-%d"},
            "v": {"type": "Float", "dtype": "float64"},
        },
    )


def test_the_task_publishes_the_series_and_its_grid_in_time_order():
    dates = ["2020-03-01", "2020-01-01", "2020-04-01", "2020-02-01"]

    prepared = SingleSeriesForecastingTask().prepare_series(
        _dataset(dates, [30.0, 10.0, 40.0, 20.0]), ["date"], ["v"]
    )

    assert list(prepared.values) == [10.0, 20.0, 30.0, 40.0]
    assert prepared.grid.freq == "MS"
    assert prepared.grid.n_steps == 4
    assert list(prepared.dataset.to_pandas()["v"]) == [10.0, 20.0, 30.0, 40.0]


def test_the_task_refuses_a_series_with_a_gap_while_preparing():
    dates = ["2020-01-01", "2020-02-01", "2020-04-01", "2020-05-01", "2020-06-01"]

    with pytest.raises(ValueError, match="misses 1 period"):
        SingleSeriesForecastingTask().prepare_for_task(
            _dataset(dates, [1.0, 2.0, 3.0, 4.0, 5.0]), ["date"], ["v"]
        )


def test_a_short_monthly_series_with_a_gap_has_no_frequency_to_infer():
    # A month has no fixed length, so it needs a regular stretch of three
    # dates; with none, the refusal says the frequency cannot be inferred.
    dates = ["2020-01-01", "2020-02-01", "2020-04-01", "2020-05-01"]

    with pytest.raises(ValueError, match="do not follow a regular frequency"):
        SingleSeriesForecastingTask().prepare_for_task(
            _dataset(dates, [1.0, 2.0, 3.0, 4.0]), ["date"], ["v"]
        )
