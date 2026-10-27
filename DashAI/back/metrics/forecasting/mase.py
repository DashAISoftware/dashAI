"""DashAI MASE forecasting metric implementation."""

from DashAI.back.core.utils import MultilingualString
from DashAI.back.metrics.forecasting_metric import ForecastingMetric, ScoredForecast
from DashAI.back.metrics.undefined_metric import UndefinedMetricError


class MASE(ForecastingMetric):
    """Mean absolute error, scaled by the seasonal naive error of the history.

    Mean Absolute Scaled Error divides a forecast's MAE by the mean absolute
    change from one season to the next over the history the model was fitted
    on, which is the in-sample error of the seasonal naive forecast. A value
    below 1 beats that baseline on average; above 1 does worse. It has no
    unit, so it compares forecasts across series of any scale, and unlike MAPE
    it stays defined when the series reaches zero.

    ::

        MASE = mean |y - y'|  /  mean_{t > m} |h_t - h_{t-m}|

    with ``h`` the history and ``m`` the season length (1 without a season).
    Range: [0, +inf), lower is better.

    References
    ----------
    - [1] https://otexts.com/fpp3/accuracy.html#scaled-errors
    """

    DESCRIPTION = MultilingualString(
        en=(
            "The forecast's average error divided by the average change from "
            "one season to the next in the history. Below 1 beats the seasonal "
            "naive forecast; comparable across series of any scale."
        ),
        es=(
            "El error promedio del pronostico dividido por el cambio promedio "
            "de una temporada a la siguiente en la historia. Bajo 1 supera al "
            "pronostico ingenuo estacional; comparable entre series de "
            "cualquier escala."
        ),
        pt=(
            "O erro medio da previsao dividido pela variacao media de uma "
            "temporada para a seguinte no historico. Abaixo de 1 supera a "
            "previsao ingenua sazonal; comparavel entre series de qualquer "
            "escala."
        ),
        de=(
            "Der mittlere Fehler der Prognose geteilt durch die mittlere "
            "Aenderung von einer Saison zur naechsten in der Historie. Unter 1 "
            "schlaegt die saisonale naive Prognose; vergleichbar ueber Reihen "
            "jeder Groessenordnung."
        ),
        zh=(
            "预测的平均误差除以历史中相邻季节之间的平均变化。"
            "小于 1 表示优于季节性朴素预测；可在任意量级的序列之间比较。"
        ),
    )

    @classmethod
    def score_forecast(cls, forecast: ScoredForecast) -> float:
        """Score a forecast's MAE against the seasonal naive error of its history.

        Raises
        ------
        UndefinedMetricError
            If the history is not longer than one season, or does not change
            from one season to the next, so there is no scale to divide by.
        """
        import numpy as np

        history = np.asarray(forecast.history, dtype=float)
        m = max(1, int(forecast.season_length))
        if len(history) <= m:
            raise UndefinedMetricError(
                f"MASE scales the error by the change across a season of {m} "
                f"step(s), and a history of {len(history)} has none."
            )
        scale = float(np.mean(np.abs(history[m:] - history[:-m])))
        if scale == 0:
            raise UndefinedMetricError(
                "MASE scales the error by how much the history changes from "
                "one season to the next, and this history does not change."
            )
        actual = np.asarray(forecast.actual, dtype=float)
        point = np.asarray(forecast.point, dtype=float)
        return float(np.mean(np.abs(actual - point)) / scale)
