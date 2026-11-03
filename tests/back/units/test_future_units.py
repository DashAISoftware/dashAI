"""Contract tests of the units that forecast with future exogenous values.

``PrepareFutureUnit`` checks the rows a user brings for the steps after the
series, and ``ForecastFutureUnit`` forecasts them (RECONCILING_FORECASTING
§2.14, decisions 5 and 6; §7.2, decision 2). The context is built by hand
(ATOMIZING §6).
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.models.forecasting.arima import ARIMA
from DashAI.back.tasks.time_grid import TimeGrid
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_future_unit import ForecastFutureUnit
from DashAI.back.units.prepare_future_unit import PrepareFutureUnit

GRID = TimeGrid(
    freq="MS",
    first=pd.Timestamp("2020-01-01"),
    last=pd.Timestamp("2021-12-01"),
    n_steps=24,
)
SCHEMA = {
    "date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "promo": {"type": "Float", "dtype": "float64"},
    "sales": {"type": "Float", "dtype": "float64"},
    "note": {"type": "Float", "dtype": "float64"},
}
NEXT = ["2022-01-01", "2022-02-01", "2022-03-01"]


def _rows(**columns):
    frame = pd.DataFrame(columns)
    return transform_dataset_with_schema(
        to_dashai_dataset(frame), {name: SCHEMA[name] for name in frame.columns}
    )


def _model():
    steps = np.arange(24.0)
    promo = (steps % 3 == 1).astype(float).reshape(-1, 1)
    model = ARIMA(p=1, d=0, q=0).fit(10 + steps + 5 * promo[:, 0], promo)
    model.time_grid = GRID.to_ref()
    return model


def _prepared(dataset, model=None):
    ctx = ExecutionContext()
    ctx.put("dataset", dataset)
    ctx.put("model", model or _model())
    PrepareFutureUnit(
        time_index="date", exogenous_columns=[{"name": "promo", "type": "Float"}]
    )(ctx)
    return ctx


def test_the_future_comes_out_in_date_order_with_only_what_the_run_reads():
    shuffled = _rows(
        date=[NEXT[2], NEXT[0], NEXT[1]],
        promo=[0.0, 1.0, 0.0],
        sales=[9.0, 9.0, 9.0],
        note=[1.0, 2.0, 3.0],
    )

    future = _prepared(shuffled).require("dataset").to_pandas()

    # The series and the columns no step reads are left out, as in x/y.
    assert list(future.columns) == ["date", "promo"]
    assert list(future["date"]) == NEXT
    assert list(future["promo"]) == [1.0, 0.0, 0.0]


@pytest.mark.parametrize(
    ("dates", "match"),
    [
        (["2022-01-01", "2022-03-01"], "2022-02-01"),
        (["2022-01-01", "2022-01-01"], "repeats.*2022-01-01"),
        (["2022-02-01", "2022-03-01"], "2022-01-01"),
    ],
    ids=["a step missing", "a date repeated", "not from the next step"],
)
def test_the_future_has_to_be_the_next_steps_of_the_grid(dates, match):
    with pytest.raises(JobError, match=match):
        _prepared(_rows(date=dates, promo=[1.0] * len(dates)))


def test_a_column_the_run_reads_has_to_be_there():
    with pytest.raises(JobError, match="'promo'"):
        _prepared(_rows(date=NEXT, note=[1.0, 2.0, 3.0]))


def test_a_gap_names_the_column_and_the_date():
    with pytest.raises(JobError, match=r"'promo'.*2022-02-01"):
        _prepared(_rows(date=NEXT, promo=[1.0, np.nan, 0.0]))


def test_a_number_recorded_as_integer_is_taken_as_float():
    ctx = ExecutionContext()
    ctx.put("dataset", _rows(date=NEXT, promo=[1.0, 0.0, 0.0]))
    ctx.put("model", _model())

    PrepareFutureUnit(
        time_index="date", exogenous_columns=[{"name": "promo", "type": "Integer"}]
    )(ctx)

    assert list(ctx.require("dataset").to_pandas()["promo"]) == [1.0, 0.0, 0.0]


def test_a_type_other_than_the_one_recorded_is_refused_naming_the_column():
    ctx = ExecutionContext()
    ctx.put("dataset", _rows(date=NEXT, promo=[1.0, 0.0, 0.0]))
    ctx.put("model", _model())

    with pytest.raises(JobError, match=r"'promo' is Float.*as Categorical"):
        PrepareFutureUnit(
            time_index="date",
            exogenous_columns=[{"name": "promo", "type": "Categorical"}],
        )(ctx)


def test_the_steps_are_forecast_with_their_exogenous_values():
    model = _model()
    ctx = _prepared(_rows(date=NEXT, promo=[1.0, 0.0, 0.0]), model)
    ctx.put("model_input", ctx.require("dataset"))

    ForecastFutureUnit(exogenous_columns=["promo"])(ctx)

    expected = model.predict(3, x_future=np.array([[1.0], [0.0], [0.0]])).point
    assert list(ctx.require("y_pred")) == pytest.approx(list(expected), rel=1e-12)
    # The rows the prediction is saved next to are the future the user gave.
    assert list(ctx.require("dataset").to_pandas()["promo"]) == [1.0, 0.0, 0.0]


def test_a_model_without_a_grid_cannot_date_the_future():
    model = _model()
    model.time_grid = None

    with pytest.raises(JobError, match="no grid"):
        _prepared(_rows(date=NEXT, promo=[1.0, 0.0, 0.0]), model)
