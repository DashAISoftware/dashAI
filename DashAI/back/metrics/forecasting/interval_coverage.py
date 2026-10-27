"""DashAI prediction interval coverage metric implementation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.metrics.forecasting_metric import ForecastingMetric, ScoredForecast
from DashAI.back.metrics.undefined_metric import UndefinedMetricError


class IntervalCoverage(ForecastingMetric):
    """The share of actual values that fall inside the 95% prediction interval.

    A 95% interval should hold about 95% of what actually happens. Coverage
    well below that says the model is more confident than it has reason to be;
    well above, that its intervals are wider than they need to be. It judges
    the intervals, not the point forecast, so it belongs beside an error
    metric rather than in place of one.

    Range: [0, 1]. Higher means more of the actual values were bounded, which
    is not the same as better: a model is well calibrated near 0.95. It is not
    meant to be optimized, since the widest intervals would win.
    """

    LEVEL = 95
    MAXIMIZE: bool = True

    DESCRIPTION = MultilingualString(
        en=(
            "The share of actual values inside the 95% prediction interval. A "
            "well calibrated model scores close to 0.95."
        ),
        es=(
            "La proporcion de valores reales dentro del intervalo de "
            "prediccion del 95%. Un modelo bien calibrado obtiene cerca de 0.95."
        ),
        pt=(
            "A proporcao de valores reais dentro do intervalo de previsao de "
            "95%. Um modelo bem calibrado obtem perto de 0.95."
        ),
        de=(
            "Der Anteil der tatsaechlichen Werte innerhalb des "
            "95-%-Prognoseintervalls. Ein gut kalibriertes Modell liegt nahe "
            "0.95."
        ),
        zh="实际值落在 95% 预测区间内的比例。校准良好的模型接近 0.95。",
    )

    @classmethod
    def score_forecast(cls, forecast: ScoredForecast) -> float:
        """The share of actual values within the forecast's 95% bounds.

        Raises
        ------
        UndefinedMetricError
            If the forecast has no 95% interval, because the model gives none,
            or its bounds are not numbers.
        """
        import numpy as np

        if cls.LEVEL not in forecast.lower or cls.LEVEL not in forecast.upper:
            raise UndefinedMetricError(
                f"The model gives no {cls.LEVEL}% prediction interval to "
                "measure the coverage of."
            )
        lower = np.asarray(forecast.lower[cls.LEVEL], dtype=float)
        upper = np.asarray(forecast.upper[cls.LEVEL], dtype=float)
        if not (np.isfinite(lower).all() and np.isfinite(upper).all()):
            raise UndefinedMetricError(
                f"The {cls.LEVEL}% prediction interval has bounds that are not "
                "numbers: the history was too short to measure its spread."
            )
        actual = np.asarray(forecast.actual, dtype=float)
        return float(np.mean((lower <= actual) & (actual <= upper)))
