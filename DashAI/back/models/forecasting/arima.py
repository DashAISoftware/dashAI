from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import BaseSchema, int_field, search_space
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    EXOGENOUS_OPTIONAL,
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np


def _order_field(letter: str, meaning: MultilingualString, upper: int):
    """Build one of the three ARIMA order fields.

    The three share a shape and differ only in what they mean, so writing them
    out separately would be three copies of the same twelve lines.

    Parameters
    ----------
    letter : str
        The conventional name of the term, ``p``, ``d`` or ``q``.
    meaning : MultilingualString
        The description shown to the user.
    upper : int
        Upper bound offered when the value is optimized.

    Returns
    -------
    Any
        A configured schema field.
    """
    return search_space(
        int_field(ge=0),
        fixed=1 if letter != "q" else 0,
        low=0,
        high=upper,
        description=meaning,
        alias=MultilingualString(
            en=f"Order {letter}",
            es=f"Orden {letter}",
            pt=f"Ordem {letter}",
            de=f"Ordnung {letter}",
            zh=f"阶数 {letter}",
        ),
    )


def _seasonal_order_field(letter: str, meaning: MultilingualString, upper: int):
    """Build one of the three seasonal order fields, off by default.

    Parameters
    ----------
    letter : str
        The conventional name of the term, ``P``, ``D`` or ``Q``.
    meaning : MultilingualString
        The description shown to the user.
    upper : int
        Upper bound offered when the value is optimized.

    Returns
    -------
    Any
        A configured schema field.
    """
    return search_space(
        int_field(ge=0),
        fixed=0,
        low=0,
        high=upper,
        description=meaning,
        alias=MultilingualString(
            en=f"Seasonal order {letter}",
            es=f"Orden estacional {letter}",
            pt=f"Ordem sazonal {letter}",
            de=f"Saisonale Ordnung {letter}",
            zh=f"季节阶数 {letter}",
        ),
    )


class ARIMASchema(BaseSchema):
    """Schema that configures the ARIMA model."""

    p: _order_field(
        "p",
        MultilingualString(
            en=(
                "How many past values the forecast is a weighted sum of, the "
                "autoregressive order."
            ),
            es=(
                "De cuantos valores pasados es suma ponderada el pronostico, "
                "el orden autorregresivo."
            ),
            pt=(
                "De quantos valores passados a previsao e soma ponderada, a "
                "ordem autorregressiva."
            ),
            de=(
                "Aus wie vielen vergangenen Werten die Prognose gewichtet "
                "gebildet wird, die autoregressive Ordnung."
            ),
            zh="预测由多少个过去的值加权求和得到，即自回归阶数。",
        ),
        5,
    )  # type: ignore
    d: _order_field(
        "d",
        MultilingualString(
            en=(
                "How many times to difference the series before modelling it. "
                "1 removes a straight trend, 0 suits a series that already "
                "hovers around a fixed level."
            ),
            es=(
                "Cuantas veces diferenciar la serie antes de modelarla. 1 "
                "elimina una tendencia lineal, 0 sirve para una serie que ya "
                "oscila alrededor de un nivel fijo."
            ),
            pt=(
                "Quantas vezes diferenciar a serie antes de modela-la. 1 "
                "remove uma tendencia linear, 0 serve para uma serie que ja "
                "oscila em torno de um nivel fixo."
            ),
            de=(
                "Wie oft die Reihe vor der Modellierung differenziert wird. 1 "
                "entfernt einen linearen Trend, 0 passt zu einer Reihe, die "
                "bereits um ein festes Niveau schwankt."
            ),
            zh=(
                "建模前对序列做几次差分。1 可去除线性趋势，"
                "0 适用于已经围绕固定水平波动的序列。"
            ),
        ),
        2,
    )  # type: ignore
    q: _order_field(
        "q",
        MultilingualString(
            en=(
                "How many past forecast errors feed into the next forecast, "
                "the moving average order."
            ),
            es=(
                "Cuantos errores de pronostico pasados alimentan el siguiente "
                "pronostico, el orden de media movil."
            ),
            pt=(
                "Quantos erros de previsao passados alimentam a proxima "
                "previsao, a ordem de media movel."
            ),
            de=(
                "Wie viele vergangene Prognosefehler in die naechste Prognose "
                "einfliessen, die Ordnung des gleitenden Mittels."
            ),
            zh="有多少个过去的预测误差参与下一次预测，即移动平均阶数。",
        ),
        5,
    )  # type: ignore
    seasonal_p: _seasonal_order_field(
        "P",
        MultilingualString(
            en=(
                "The autoregressive order of the seasonal part: how many past "
                "seasons the forecast is a weighted sum of. 0 leaves it out."
            ),
            es=(
                "El orden autorregresivo de la parte estacional: de cuantas "
                "temporadas pasadas es suma ponderada el pronostico. 0 la omite."
            ),
            pt=(
                "A ordem autorregressiva da parte sazonal: de quantas temporadas "
                "passadas a previsao e soma ponderada. 0 a omite."
            ),
            de=(
                "Die autoregressive Ordnung des saisonalen Teils: aus wie vielen "
                "vergangenen Saisons die Prognose gewichtet gebildet wird. 0 "
                "laesst ihn weg."
            ),
            zh=(
                "季节部分的自回归阶数：预测由多少个过去的季节加权求和得到。"
                "0 表示不使用。"
            ),
        ),
        2,
    )  # type: ignore
    seasonal_d: _seasonal_order_field(
        "D",
        MultilingualString(
            en=(
                "How many times to difference the series a season apart. 1 "
                "removes a pattern that repeats every season."
            ),
            es=(
                "Cuantas veces diferenciar la serie con una temporada de "
                "distancia. 1 elimina un patron que se repite cada temporada."
            ),
            pt=(
                "Quantas vezes diferenciar a serie com uma temporada de "
                "distancia. 1 remove um padrao que se repete a cada temporada."
            ),
            de=(
                "Wie oft die Reihe im Abstand einer Saison differenziert wird. "
                "1 entfernt ein Muster, das sich jede Saison wiederholt."
            ),
            zh="以一个季节为间隔对序列做几次差分。1 可去除每个季节重复的模式。",
        ),
        1,
    )  # type: ignore
    seasonal_q: _seasonal_order_field(
        "Q",
        MultilingualString(
            en=(
                "The moving average order of the seasonal part: how many past "
                "seasonal errors feed into the next forecast."
            ),
            es=(
                "El orden de media movil de la parte estacional: cuantos errores "
                "estacionales pasados alimentan el siguiente pronostico."
            ),
            pt=(
                "A ordem de media movel da parte sazonal: quantos erros sazonais "
                "passados alimentam a proxima previsao."
            ),
            de=(
                "Die Ordnung des gleitenden Mittels im saisonalen Teil: wie "
                "viele vergangene saisonale Fehler in die naechste Prognose "
                "einfliessen."
            ),
            zh="季节部分的移动平均阶数：有多少个过去的季节误差参与下一次预测。",
        ),
        2,
    )  # type: ignore
    season_length: search_space(
        int_field(ge=1),
        fixed=1,
        low=1,
        high=12,
        description=MultilingualString(
            en=(
                "How many steps make up one season, which the seasonal orders "
                "count in: 12 for monthly data repeating yearly, 7 for daily "
                "data repeating weekly. It has to be at least 2 when a "
                "seasonal order is above 0."
            ),
            es=(
                "Cuantos pasos forman una temporada, en la que cuentan los "
                "ordenes estacionales: 12 para datos mensuales que se repiten "
                "cada ano, 7 para datos diarios que se repiten cada semana. "
                "Tiene que ser al menos 2 si algun orden estacional es mayor "
                "que 0."
            ),
            pt=(
                "Quantos passos formam uma temporada, na qual contam as ordens "
                "sazonais: 12 para dados mensais que se repetem a cada ano, 7 "
                "para dados diarios que se repetem a cada semana. Tem que ser "
                "pelo menos 2 se alguma ordem sazonal for maior que 0."
            ),
            de=(
                "Wie viele Schritte eine Saison bilden, in der die saisonalen "
                "Ordnungen zaehlen: 12 fuer monatliche Daten mit jaehrlicher "
                "Wiederholung, 7 fuer taegliche Daten mit woechentlicher. "
                "Mindestens 2, wenn eine saisonale Ordnung groesser als 0 ist."
            ),
            zh=(
                "一个季节包含多少步，季节阶数以此计数：按年重复的月度数据为 12，"
                "按周重复的日数据为 7。任一季节阶数大于 0 时至少为 2。"
            ),
        ),
        alias=MultilingualString(
            en="Season length",
            es="Largo de temporada",
            pt="Comprimento da temporada",
            de="Saisonlaenge",
            zh="季节长度",
        ),
    )  # type: ignore


class ARIMA(SingleSeriesForecastingModel):
    """Model a series as its own past values plus its own past errors.

    ARIMA combines three ideas, one per order. The autoregressive part (``p``)
    makes the forecast a weighted sum of recent values. The differencing part
    (``d``) subtracts consecutive observations until what is left has no trend,
    which is what lets the other two parts assume a stable level. The moving
    average part (``q``) lets recent forecast errors feed back in.

    A seasonal part repeats the same three ideas a season apart: ``P``, ``D``
    and ``Q``, counted in seasons of ``season_length`` steps. It is off by
    default (all three at 0), which is the plain ARIMA.

    The orders are not chosen automatically. ``d = 1`` suits a series that
    trends, ``d = 0`` one that hovers around a level, and the DashAI optimizer
    can search them when told to.

    statsmodels' ``ARIMA`` is already a state space SARIMAX: it takes the
    seasonal orders and exogenous variables, and its forecasts come with
    prediction intervals. Nothing is reimplemented.

    References
    ----------
    - [1] https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html
    - [2] https://otexts.com/fpp3/arima.html
    """

    SCHEMA = ARIMASchema
    DESCRIPTION = MultilingualString(
        en=(
            "Models a series from its own past values and past errors, after "
            "differencing away any trend. The standard reference model for a "
            "series without strong seasonality."
        ),
        es=(
            "Modela una serie a partir de sus propios valores y errores "
            "pasados, tras eliminar la tendencia por diferenciacion. El modelo "
            "de referencia estandar para series sin estacionalidad marcada."
        ),
        pt=(
            "Modela uma serie a partir dos seus proprios valores e erros "
            "passados, apos remover a tendencia por diferenciacao. O modelo de "
            "referencia padrao para series sem sazonalidade forte."
        ),
        de=(
            "Modelliert eine Reihe aus ihren eigenen vergangenen Werten und "
            "Fehlern, nachdem ein Trend wegdifferenziert wurde. Das "
            "Standardreferenzmodell fuer Reihen ohne starke Saisonalitaet."
        ),
        zh=(
            "在通过差分消除趋势后，用序列自身的历史值和历史误差建模。"
            "这是无明显季节性序列的标准参考模型。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="ARIMA", es="ARIMA", pt="ARIMA", de="ARIMA", zh="ARIMA"
    )

    EXOGENOUS = EXOGENOUS_OPTIONAL
    SUPPORTS_INTERVALS = True

    def __init__(
        self,
        p: int = 1,
        d: int = 1,
        q: int = 0,
        seasonal_p: int = 0,
        seasonal_d: int = 0,
        seasonal_q: int = 0,
        season_length: int = 1,
        **kwargs,
    ):
        """Initialise the model with its orders.

        Parameters
        ----------
        p, d, q : int
            Autoregressive order, number of differences and moving average
            order.
        seasonal_p, seasonal_d, seasonal_q : int
            The same three for the seasonal part, 0 to leave it out.
        season_length : int
            Steps per season, at least 2 when a seasonal order is above 0.
        **kwargs
            Ignored, accepted for consistency with the other models.

        Raises
        ------
        ValueError
            If a seasonal order is above 0 and the season is shorter than 2.
        """
        super().__init__(**kwargs)
        if (seasonal_p or seasonal_d or seasonal_q) and season_length < 2:
            raise ValueError(
                "A seasonal part needs a season length of at least 2, got "
                f"{season_length}."
            )
        self.p, self.d, self.q = p, d, q
        self.seasonal_p, self.seasonal_d, self.seasonal_q = (
            seasonal_p,
            seasonal_d,
            seasonal_q,
        )
        self.season_length = season_length
        self._result = None

    def _seasonal_order(self) -> tuple:
        """The seasonal order statsmodels takes, all zeros when it is off."""
        if not (self.seasonal_p or self.seasonal_d or self.seasonal_q):
            return (0, 0, 0, 0)
        return (self.seasonal_p, self.seasonal_d, self.seasonal_q, self.season_length)

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Fit the ARIMA model to the series.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        x : array-like, optional
            Exogenous variables, one row per step.

        Raises
        ------
        ValueError
            If the series is too short for the requested orders.
        """
        import warnings

        from statsmodels.tsa.arima.model import ARIMA as _ARIMA

        seasonal = self.seasonal_p + self.seasonal_d + self.seasonal_q
        needed = self.p + self.d + self.q + self.season_length * seasonal
        if len(y) <= needed:
            raise ValueError(
                f"An ARIMA{(self.p, self.d, self.q)}x{self._seasonal_order()} "
                f"needs more than {needed} observations, but the series has "
                f"{len(y)}."
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._result = _ARIMA(
                y,
                exog=x,
                order=(self.p, self.d, self.q),
                seasonal_order=self._seasonal_order(),
            ).fit()

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Forecast the next ``h`` steps after the end of the history.

        Parameters
        ----------
        h : int
            How many steps to forecast.
        x_future : array-like, optional
            Exogenous variables for the forecast steps.

        Returns
        -------
        np.ndarray
            One value per step, in order.
        """
        return self._result.forecast(steps=h, exog=x_future)

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """The state space model's own prediction intervals."""
        import numpy as np

        forecast = self._result.get_forecast(steps=h, exog=x_future)
        lower, upper = {}, {}
        for level in levels:
            bounds = np.asarray(forecast.conf_int(alpha=1 - level / 100.0))
            lower[level], upper[level] = bounds[:, 0], bounds[:, 1]
        return lower, upper
