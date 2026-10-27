from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np


class NaiveForecasterSchema(BaseSchema):
    """Schema for NaiveForecaster. It has nothing to configure."""


class NaiveForecaster(SingleSeriesForecastingModel):
    """Predict that the series stays where it last was.

    Every future value is forecast as the final observed value. There is
    nothing to fit and nothing to tune.

    Its worth is as a yardstick, not as a forecast. A model that cannot beat
    this one has found nothing in the data, and until now DashAI gave no way
    to check that. On a random walk it is provably the best possible forecast,
    which is precisely why beating it on real series is harder than people
    expect.

    References
    ----------
    - [1] https://otexts.com/fpp3/simple-methods.html
    """

    SCHEMA = NaiveForecasterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Predicts that every future value equals the last observed one. "
            "The baseline any real forecasting model has to beat to be worth "
            "using."
        ),
        es=(
            "Predice que cada valor futuro es igual al ultimo observado. Es la "
            "linea base que cualquier modelo de pronostico real debe superar "
            "para valer la pena."
        ),
        pt=(
            "Preve que cada valor futuro e igual ao ultimo observado. E a "
            "linha de base que qualquer modelo de previsao real precisa "
            "superar para valer a pena."
        ),
        de=(
            "Sagt voraus, dass jeder zukuenftige Wert dem zuletzt beobachteten "
            "entspricht. Die Grundlinie, die jedes echte Prognosemodell "
            "schlagen muss, um sich zu lohnen."
        ),
        zh=(
            "预测每个未来值都等于最后一个观测值。"
            "这是任何真正的预测模型都必须超越的基准。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Naive Forecaster",
        es="Pronostico Ingenuo",
        pt="Previsao Ingenua",
        de="Naive Prognose",
        zh="朴素预测",
    )

    SUPPORTS_INTERVALS = True

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Remember the last value, and the spread of the one-step changes.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        X : None
            The model uses no exogenous variables.
        """
        import numpy as np

        self._last_value = float(y[-1])
        # The residual of a naive forecast is the change from one step to the
        # next. With K = 0 parameters and the first step lost, fpp3 estimates
        # the spread over the T - 1 residuals there are.
        changes = np.diff(y)
        self._sigma = (
            float(np.sqrt(np.mean(changes**2))) if len(changes) else float("nan")
        )

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Repeat the last observed value for every requested step.

        Parameters
        ----------
        h : int
            How many steps to forecast.
        x_future : None
            The model uses no exogenous variables.

        Returns
        -------
        np.ndarray
            The last observed value, repeated.
        """
        import numpy as np

        return np.full(h, self._last_value, dtype=float)

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Normal intervals whose spread grows with the square root of the step.

        fpp3 §5.5: the h-step standard deviation of a naive forecast is the
        one-step one times sqrt(h). A series of one observation has no step to
        measure, so its bounds are not a number.
        """
        import numpy as np

        sd = self._sigma * np.sqrt(np.arange(1, h + 1))
        return self._normal_bounds(self._forecast(h, None), sd, levels)
