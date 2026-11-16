"""Shared body of the units that backtest a single-series forecaster.

Plain values in and out, and never the execution context: a ``ctx.require``
or ``ctx.put`` hidden in here would be invisible to the contract audit that
parses each unit's own source (ATOMIZING_JOBS §9).
"""

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from DashAI.back.core.schema_fields import component_field, schema_field
from DashAI.back.core.utils import MultilingualString

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.models.forecasting.single_series_forecasting_model import (
        SingleSeriesForecastingModel,
    )
    from DashAI.back.tasks.time_grid import TimeGrid

#: The interval levels a backtest asks of a model that gives intervals: 95
#: is what interval coverage measures, 80 what a plot shades inside it.
LEVELS = [80, 95]


def forecasts_file(runs_path, artifact_prefix: str):
    """Where a run's backtest forecasts are kept: beside its model file.

    Derived from the run, so no column has to store it, and the same function
    is what the unit that writes it, the endpoint that reads it and the code
    that deletes a run all ask.
    """
    from pathlib import Path

    return Path(runs_path) / f"{artifact_prefix}_forecasts.json"


#: Steps in one cycle of each base step: a day repeats weekly, an hour daily,
#: a month yearly, a second every minute. "SM" is the semi-month (twice a
#: month) and "B" the business day (five a week). A step that is not here has
#: no season (1).
SEASON_BY_STEP = {
    "Y": 1,
    "Q": 4,
    "M": 12,
    "SM": 24,
    "W": 52,
    "D": 7,
    "B": 5,
    "h": 24,
    "min": 60,
    "s": 60,
}

#: The units a fixed step is counted in, from the largest: a step is read in
#: the first one that divides it whole.
WHOLE_UNITS = (("W", "7D"), ("D", "1D"), ("h", "1h"), ("min", "1min"), ("s", "1s"))


def _whole_step(offset) -> Tuple[str, int]:
    """A pandas offset as its rule code and multiple, in its largest unit.

    A fixed step can be spelled in a smaller unit than it spans: 24 hours are
    a day, 60 minutes an hour and 7 days a week. Read in the largest unit that
    divides it whole, the multiple then divides that unit's cycle. Calendar
    steps (months, business days, anchored weeks) are left as they are.

    Parameters
    ----------
    offset : pandas.DateOffset
        The offset of the grid's frequency.

    Returns
    -------
    tuple of (str, int)
        The rule code and its multiple.
    """
    import pandas as pd

    if isinstance(offset, pd.offsets.Tick):
        for name, unit in WHOLE_UNITS:
            size = pd.Timedelta(unit).value
            if offset.nanos % size == 0:
                return name, offset.nanos // size
    return offset.name, offset.n


def _base_step(rule_code: str) -> str:
    """The base step of a pandas rule code, without its anchors.

    ``"QS-JAN"`` is a quarter anchored at its start, ``"ME"`` a month at its
    end, ``"SMS-15"`` a semi-month split on the 15th and ``"BMS"`` a month
    starting on its first business day. The anchors say where a step begins,
    not how long it is, so all four count as their base step.

    Parameters
    ----------
    rule_code : str
        The ``name`` of a pandas offset, without its multiple.

    Returns
    -------
    str
        The base step, or the code unchanged when it has none the table knows.
    """
    step = rule_code.split("-")[0]
    if step in SEASON_BY_STEP:
        return step
    if step[-1:] in ("S", "E"):
        step = step[:-1]
    if step not in SEASON_BY_STEP and step[:1] == "B" and step[1:] in SEASON_BY_STEP:
        step = step[1:]
    return step


def season_length_for(freq: str) -> int:
    """The season a frequency usually implies: 12 for months, 7 for days.

    A fixed step is first read in its largest whole unit (``_whole_step``):
    every 24 hours is daily, every 7 days weekly. A multiple of the step then
    divides its cycle when it can: every 2 hours is 12 steps a day, every 15
    minutes 4 an hour. When it cannot, as every 3 days in a 7-day week, no
    season is assumed. Neither is one for a step the table does not know.

    Parameters
    ----------
    freq : str
        A pandas frequency alias, as the grid names it.

    Returns
    -------
    int
        Steps per season, 1 when the frequency implies none.
    """
    import pandas as pd

    step, n = _whole_step(pd.tseries.frequencies.to_offset(freq))
    cycle = SEASON_BY_STEP.get(_base_step(step), 1)
    if n < 1 or cycle % n:
        return 1
    return cycle // n


def with_season_from_grid(parameters: Dict[str, Any], freq: str) -> Dict[str, Any]:
    """The run's parameters, with a season left empty read from the frequency.

    A season is empty when the run leaves the key out, as the API may, or
    sends it as None, or as a search envelope whose fixed value is None, as
    the run form does with the schema's placeholder, or missing. A searched
    envelope keeps its range and its switch: only its starting value is filled.

    Parameters
    ----------
    parameters : dict
        The run's parameters for a model that declares ``season_length``.
    freq : str
        The frequency of the series' grid.

    Returns
    -------
    dict
        A copy of ``parameters`` whose ``season_length`` is set.
    """
    resolved = dict(parameters)
    value = resolved.get("season_length")
    if value is None:
        resolved["season_length"] = season_length_for(freq)
    elif isinstance(value, dict) and value.get("fixed_value") is None:
        resolved["season_length"] = {**value, "fixed_value": season_length_for(freq)}
    return resolved


def build_model(model_class: type, parameters: Dict[str, Any], run_id=None):
    """A fresh, unfitted model with the given parameter tree.

    Built through ``ModelFactory``, the way every run builds its model, so a
    parameter written as a search envelope reads as its fixed value.
    """
    from DashAI.back.models.model_factory import ModelFactory

    return ModelFactory(model_class, parameters, run_id).model


def _plain(values) -> List[Optional[float]]:
    """A JSON list of floats, with ``None`` where a value is not finite."""
    return [float(v) if math.isfinite(float(v)) else None for v in values]


def forecast_origin(
    model: "SingleSeriesForecastingModel",
    series: "np.ndarray",
    origin: int,
    horizon: int,
    grid: Optional["TimeGrid"],
    partition: str,
    index: int,
    levels: Sequence[int],
    x: Optional["np.ndarray"] = None,
) -> Dict[str, Any]:
    """Fit on the steps before an origin and forecast the horizon after it.

    ``x``, when given, is the cut's exogenous matrix, one row per step of the
    whole series: the model is fitted with its rows before the origin and
    forecasts with the horizon's rows after it.

    Returns
    -------
    dict
        The origin as the forecasts file records it: its partition, its
        place, the dates of its steps, what actually happened, the forecast
        and its bounds by level (the level as a string, as JSON keys are).
        Without a grid, as in a search trial that only scores, the dates are
        left empty.
    """
    history = None if x is None else x[:origin]
    future = None if x is None else x[origin : origin + horizon]
    model.fit(series[:origin], history)
    forecast = model.predict(horizon, x_future=future, levels=list(levels) or None)
    dates = grid.dates(origin, horizon) if grid is not None else []
    return {
        "partition": partition,
        "index": index,
        "origin_step": int(origin),
        "dates": [date.isoformat() for date in dates],
        "actual": _plain(series[origin : origin + horizon]),
        "forecast": _plain(forecast.point),
        "lower": {str(level): _plain(forecast.lower[level]) for level in levels},
        "upper": {str(level): _plain(forecast.upper[level]) for level in levels},
    }


def model_grid(model) -> "TimeGrid":
    """The grid a kept model was fitted on, which dates the steps it forecasts.

    Raises
    ------
    JobError
        If the model carries none: it was not kept by a forecasting run.
    """
    from DashAI.back.job.base_job import JobError
    from DashAI.back.tasks.time_grid import TimeGrid

    grid_ref = getattr(model, "time_grid", None)
    if not grid_ref:
        raise JobError(
            "The model has no grid to name the dates of its forecast: it "
            "was not trained by a forecasting run. Train it again."
        )
    return TimeGrid.from_ref(grid_ref)


def forecast_steps(model, horizon: int, x_future=None) -> "np.ndarray":
    """The kept model's point forecast of the steps after its series.

    Shared by the prediction by horizon and the one with future exogenous
    values, so the two fail with the same message.

    Raises
    ------
    JobError
        If the model cannot forecast them.
    """
    import logging

    from DashAI.back.job.base_job import JobError

    try:
        return model.predict(int(horizon), x_future=x_future).point
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise JobError(f"The model could not forecast {horizon} steps: {e}") from e


def exogenous_for(
    model_class: type,
    parameters: Optional[Dict[str, Any]],
    declared: bool,
    cut: Dict[str, Any],
) -> Optional["np.ndarray"]:
    """The exogenous matrix of a cut, or None when the run does not read it.

    Whether it does is ``exogenous_usage``'s answer, from what the run is
    configured with: whether the session's role has columns (``declared``),
    the model and its parameters. It is the same answer the session shows
    before training and the run records, so the three cannot disagree. A
    model that takes none, or one switched off, is never handed an ``x``.

    Raises
    ------
    JobError
        If the run reads them and this cut's preprocessing resolved the role
        to no column: the cut is not trained without them.
    """
    from DashAI.back.job.base_job import JobError
    from DashAI.back.models.forecasting.single_series_forecasting_model import (
        exogenous_usage,
    )

    used, _ = exogenous_usage(model_class, parameters, declared)
    if not used:
        return None
    if not cut["columns"]:
        raise JobError(
            f"The session's preprocessing fitted for {cut['name']} left no "
            f"exogenous column, and {model_class.__name__} reads them in this "
            "run. Change the steps that transform the exogenous variables, or "
            "turn off use_exogenous to compare the model without them."
        )
    return cut["values"]


def scored_forecast(record: Dict[str, Any], series: "np.ndarray", season_length: int):
    """An origin of the forecasts file as a metric reads it."""
    import numpy as np

    from DashAI.back.metrics.forecasting_metric import ScoredForecast

    def array(values):
        return np.array([np.nan if v is None else v for v in values], dtype=float)

    return ScoredForecast(
        actual=array(record["actual"]),
        point=array(record["forecast"]),
        lower={int(level): array(v) for level, v in record["lower"].items()},
        upper={int(level): array(v) for level, v in record["upper"].items()},
        history=np.asarray(series[: record["origin_step"]], dtype=float),
        season_length=season_length,
    )


def forecaster_field():
    """A single-series forecaster, chosen with its own configuration."""
    return schema_field(
        component_field(parent="SingleSeriesForecastingModel"),
        placeholder={"component": "NaiveForecaster", "params": {}},
        description=MultilingualString(
            en="Forecaster to instantiate, along with its own configuration.",
            es="Pronosticador a instanciar, junto con su propia configuración.",
            pt="Previsor a instanciar, junto com a sua própria configuração.",
            de="Zu instanziierendes Prognosemodell samt seiner Konfiguration.",
            zh="要实例化的预测模型及其自身配置。",
        ),
        alias=MultilingualString(
            en="Model", es="Modelo", pt="Modelo", de="Modell", zh="模型"
        ),
    )


def origin_splitter_field():
    """A splitter that cuts a series into backtest origins."""
    return schema_field(
        component_field(parent="OriginSplitter"),
        placeholder={
            "component": "RollingOriginSplitter",
            "params": {"horizon": 6, "n_origins": 3},
        },
        description=MultilingualString(
            en="Splitter that cuts the series into backtest origins, in steps.",
            es="Divisor que corta la serie en orígenes de backtest, en pasos.",
            pt="Divisor que corta a série em origens de backtest, em passos.",
            de=(
                "Aufteiler, der die Reihe in Backtest-Ursprünge schneidet, "
                "in Schritten."
            ),
            zh="以步为单位将序列切分为回测起点的划分器。",
        ),
        alias=MultilingualString(
            en="Splitter",
            es="Divisor",
            pt="Divisor",
            de="Aufteiler",
            zh="划分器",
        ),
    )
