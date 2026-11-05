from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np


class DriftForecasterSchema(BaseSchema):
    """Schema for DriftForecaster. It has nothing to configure."""


class DriftForecaster(SingleSeriesForecastingModel):
    """Extend the line from the first observation to the last.

    Each future value is the last observed one plus the average change per
    step over the whole history, times the number of steps ahead. It is the
    naive forecast with a trend: the line drawn from the first point to the
    last, carried forward.

    Its worth is as a yardstick for series with a direction. A model that
    cannot beat it has found nothing beyond the average slope.

    References
    ----------
    - [1] https://otexts.com/fpp3/simple-methods.html
    """

    SCHEMA = DriftForecasterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Extends the line from the first observation to the last: the "
            "last value plus the average change per step. A baseline for "
            "series with a steady direction."
        ),
        es=(
            "Extiende la recta que une la primera observación con la última: "
            "el último valor más el cambio promedio por paso. Una línea base "
            "para series con una dirección sostenida."
        ),
        pt=(
            "Estende a reta que liga a primeira observação à última: o último "
            "valor mais a variação média por passo. Uma linha de base para "
            "séries com uma direção sustentada."
        ),
        de=(
            "Verlängert die Linie von der ersten zur letzten Beobachtung: der "
            "letzte Wert plus die durchschnittliche Änderung pro Schritt. Eine "
            "Grundlinie für Reihen mit stetiger Richtung."
        ),
        zh=(
            "延长从第一个观测值到最后一个观测值的直线：最后一个值加上每步的"
            "平均变化。适用于方向稳定的序列的基准。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Drift Forecaster",
        es="Pronóstico con Deriva",
        pt="Previsão com Deriva",
        de="Drift-Prognose",
        zh="漂移预测",
    )
    COLOR: str = "#FFCA28"
    ICON: str = "TrendingUp"

    SUPPORTS_INTERVALS = True

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Remember the last value, the slope, and the spread around it.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        x : None
            The model uses no exogenous variables.

        Raises
        ------
        ValueError
            If the series has a single observation, which has no slope.
        """
        import numpy as np

        if len(y) < 2:
            raise ValueError(
                "The drift forecast needs at least 2 observations to measure "
                f"a slope, but the series has {len(y)}."
            )
        self._last_value = float(y[-1])
        self._n = len(y)
        self._slope = float((y[-1] - y[0]) / (self._n - 1))
        # The residual of a drift forecast is each one-step change minus the
        # slope. With K = 1 parameter (the slope) and the first step lost,
        # fpp3 estimates the spread over T - 2. Two observations leave nothing
        # to measure it with: their one change is the slope itself.
        residuals = np.diff(y) - self._slope
        self._sigma = (
            float(np.sqrt(np.sum(residuals**2) / (self._n - 2)))
            if self._n > 2
            else float("nan")
        )

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Add the slope once per step to the last observed value.

        Parameters
        ----------
        h : int
            How many steps to forecast.
        x_future : None
            The model uses no exogenous variables.

        Returns
        -------
        np.ndarray
            One value per step, in order.
        """
        import numpy as np

        return self._last_value + self._slope * np.arange(1, h + 1, dtype=float)

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Normal intervals that widen faster than the naive ones.

        fpp3 §5.5: the h-step standard deviation of a drift forecast is the
        one-step one times sqrt(h * (1 + h / (T - 1))). The extra term is the
        doubt about the slope, which grows with every step it is carried.
        """
        import numpy as np

        steps = np.arange(1, h + 1, dtype=float)
        sd = self._sigma * np.sqrt(steps * (1 + steps / (self._n - 1)))
        return self._normal_bounds(self._forecast(h, None), sd, levels)
