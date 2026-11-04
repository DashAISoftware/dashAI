from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np


class MeanForecasterSchema(BaseSchema):
    """Schema for MeanForecaster. It has nothing to configure."""


class MeanForecaster(SingleSeriesForecastingModel):
    """Predict that every future value equals the average of the history.

    Every future value is forecast as the mean of all the observed ones. There
    is nothing to tune.

    Like the naive forecast, its worth is as a yardstick. It suits a series
    that wanders around a fixed level with no memory, where the last value
    says no more than any other. A model that cannot beat it has not even
    found that the series moves.

    References
    ----------
    - [1] https://otexts.com/fpp3/simple-methods.html
    """

    SCHEMA = MeanForecasterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Predicts that every future value equals the average of the whole "
            "history. A baseline for series that move around a fixed level."
        ),
        es=(
            "Predice que cada valor futuro es igual al promedio de toda la "
            "historia. Una línea base para series que se mueven en torno a un "
            "nivel fijo."
        ),
        pt=(
            "Prevê que cada valor futuro é igual à média de todo o histórico. "
            "Uma linha de base para séries que se movem em torno de um nível "
            "fixo."
        ),
        de=(
            "Sagt voraus, dass jeder zukünftige Wert dem Mittelwert der "
            "gesamten Historie entspricht. Eine Grundlinie für Reihen, die um "
            "ein festes Niveau schwanken."
        ),
        zh="预测每个未来值都等于全部历史的平均值。适用于围绕固定水平波动的序列的基准。",
    )
    DISPLAY_NAME = MultilingualString(
        en="Mean Forecaster",
        es="Pronóstico de la Media",
        pt="Previsão pela Média",
        de="Mittelwert-Prognose",
        zh="均值预测",
    )

    SUPPORTS_INTERVALS = True

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Remember the mean, and the spread of the values around it.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        x : None
            The model uses no exogenous variables.
        """
        import numpy as np

        self._mean = float(np.mean(y))
        self._n = len(y)
        # The residual of a mean forecast is the distance of each value from
        # the mean. With K = 1 parameter (the mean) and no step lost, fpp3
        # estimates the spread over T - 1.
        residuals = y - self._mean
        self._sigma = (
            float(np.sqrt(np.sum(residuals**2) / (self._n - 1)))
            if self._n > 1
            else float("nan")
        )

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Repeat the mean of the history for every requested step.

        Parameters
        ----------
        h : int
            How many steps to forecast.
        x_future : None
            The model uses no exogenous variables.

        Returns
        -------
        np.ndarray
            The mean of the history, repeated.
        """
        import numpy as np

        return np.full(h, self._mean, dtype=float)

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Normal intervals of the same width at every step.

        fpp3 §5.5: the h-step standard deviation of a mean forecast is the
        one-step one times sqrt(1 + 1/T), whatever the step, since the mean
        does not drift. A series of one observation has no spread to measure,
        so its bounds are not a number.
        """
        import numpy as np

        sd = np.full(h, self._sigma * np.sqrt(1 + 1 / self._n))
        return self._normal_bounds(self._forecast(h, None), sd, levels)
