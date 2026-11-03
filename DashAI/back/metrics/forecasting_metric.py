"""How a forecast is scored, and the metrics only a forecast has.

A forecast carries more than a run's predictions: the bounds of its intervals,
and the history the model was fitted on, which MASE scales its error by. So a
forecast is scored with ``score_forecast(forecast)``, which every metric that
forecasting offers answers:

- a point metric (MAE, RMSE, MAPE, SMAPE) through ``PointMetricMixin``, a one
  line adapter to its own ``score(actual, point)``, so the arithmetic exists
  once whichever task asks;
- a ``ForecastingMetric`` (MASE, interval coverage) by reading what it needs
  off the forecast.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.metrics.undefined_metric import UndefinedMetricError

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class ScoredForecast:
    """A forecast next to what actually happened, as a metric reads it.

    Attributes
    ----------
    actual : numpy.ndarray
        The observed values of the forecast steps.
    point : numpy.ndarray
        The point forecast of the same steps.
    lower, upper : dict of int to numpy.ndarray
        The interval bounds at each level the model gave, in percent.
    history : numpy.ndarray
        The values the model was fitted on, in time order.
    season_length : int
        Steps per season of the series, 1 when it has none.
    """

    actual: "np.ndarray"
    point: "np.ndarray"
    lower: Dict[int, "np.ndarray"] = field(default_factory=dict)
    upper: Dict[int, "np.ndarray"] = field(default_factory=dict)
    history: "np.ndarray" = None
    season_length: int = 1


class PointMetricMixin:
    """Score a forecast by its point values, through the metric's ``score``.

    Not a ``Base*`` class and no ``TYPE``: the registry finds a component's
    type by the one ancestor that has both, and a second would break every
    metric that inherits this.
    """

    @classmethod
    def score_forecast(cls, forecast: ScoredForecast) -> float:
        """The metric's ``score`` on the actual values and the point forecast."""
        return cls.score(forecast.actual, forecast.point)


class ForecastingMetric(BaseMetric):
    """Base class of the metrics that forecasting offers and regression does not.

    MASE needs the history a model was fitted on and the season length, and
    interval coverage the bounds of the forecast: neither has a value on a
    run's rows alone. MAPE and SMAPE live here too for now, so that forecasting
    offers them and regression does not until its results show why a metric
    is unavailable (RECONCILING_FORECASTING §2.13).
    """

    MAXIMIZE: bool = False
    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]

    @classmethod
    def score_forecast(cls, forecast: ScoredForecast) -> float:
        """Score a forecast against what actually happened."""
        raise NotImplementedError(f"{cls.__name__} must say how it scores a forecast.")

    @classmethod
    def score(cls, true_values, pred_values) -> float:
        """A forecasting metric has no value on a run's rows alone.

        Raises
        ------
        UndefinedMetricError
            Always: the metric reads a forecast, not two columns. A session
            that lists it for a task scored by rows records it as unavailable.
        """
        raise UndefinedMetricError(
            f"{cls.__name__} scores a forecast against the history it was "
            "fitted on, so it has no value on rows alone."
        )
