"""Shared body of the units that backtest a single-series forecaster.

Plain values in and out, and never the execution context: a ``ctx.require``
or ``ctx.put`` hidden in here would be invisible to the contract audit that
parses each unit's own source (ATOMIZING_JOBS §9).
"""

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

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

#: Steps per season, by the kind of step a frequency names. A series whose
#: step is not here has no season assumed (1).
SEASON_BY_STEP = {
    "Y": 1,
    "Q": 4,
    "M": 12,
    "W": 52,
    "D": 7,
    "B": 5,
    "h": 24,
    "min": 60,
}


def season_length_for(freq: str) -> int:
    """The season a frequency usually implies: 12 for months, 7 for days.

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

    # "QS-JAN" is a quarter anchored at its start, "ME" a month at its end:
    # the anchor says where a step begins, not how long it is.
    step = pd.tseries.frequencies.to_offset(freq).name.split("-")[0]
    if step not in SEASON_BY_STEP and step[-1:] in ("S", "E"):
        step = step[:-1]
    return SEASON_BY_STEP.get(step, 1)


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
) -> Dict[str, Any]:
    """Fit on the steps before an origin and forecast the horizon after it.

    Returns
    -------
    dict
        The origin as the forecasts file records it: its partition, its
        place, the dates of its steps, what actually happened, the forecast
        and its bounds by level (the level as a string, as JSON keys are).
        Without a grid, as in a search trial that only scores, the dates are
        left empty.
    """
    model.fit(series[:origin])
    forecast = model.predict(horizon, levels=list(levels) or None)
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
            es="Particionador que corta la serie en origenes de backtest, en pasos.",
            pt="Divisor que corta a serie em origens de backtest, em passos.",
            de="Splitter, der die Reihe in Backtest-Ursprunge schneidet, in Schritten.",
            zh="以步为单位将序列切分为回测起点的划分器。",
        ),
        alias=MultilingualString(
            en="Splitter",
            es="Particionador",
            pt="Divisor",
            de="Splitter",
            zh="划分器",
        ),
    )
