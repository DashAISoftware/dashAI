from typing import TYPE_CHECKING

from DashAI.back.core.schema_fields import BaseSchema, optimizer_int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


def _order_field(
    name: str, meaning: MultilingualString, default: int, upper: int, alias: str
):
    """Build one of the seven SARIMAX order fields.

    The seven share a shape and differ only in what they mean and where they
    start, so writing them out separately would be seven copies of the same
    twelve lines.

    Parameters
    ----------
    name : str
        The conventional name of the term, for example ``p`` or ``P``.
    meaning : MultilingualString
        The description shown to the user.
    default : int
        Value used when the user does not change it.
    upper : int
        Upper bound offered when the value is optimized.
    alias : str
        Label shown beside the field.

    Returns
    -------
    Any
        A configured schema field.
    """
    return schema_field(
        optimizer_int_field(ge=0),
        placeholder={
            "optimize": False,
            "fixed_value": default,
            "lower_bound": 0,
            "upper_bound": upper,
        },
        description=meaning,
        alias=MultilingualString(en=alias, es=alias, pt=alias, de=alias, zh=alias),
    )


class SARIMAXSchema(BaseSchema):
    """Schema that configures the SARIMAX model."""

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
        1,
        5,
        "Order p",
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
        1,
        2,
        "Order d",
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
        0,
        5,
        "Order q",
    )  # type: ignore
    seasonal_p: _order_field(
        "P",
        MultilingualString(
            en=(
                "The autoregressive order across seasons: how many values one "
                "season apart, two seasons apart and so on the forecast is a "
                "weighted sum of."
            ),
            es=(
                "El orden autorregresivo entre estaciones: de cuantos valores "
                "separados por una estacion, dos estaciones y asi es suma "
                "ponderada el pronostico."
            ),
            pt=(
                "A ordem autorregressiva entre estacoes: de quantos valores "
                "separados por uma estacao, duas estacoes e assim por diante a "
                "previsao e soma ponderada."
            ),
            de=(
                "Die autoregressive Ordnung ueber Saisons hinweg: aus wie "
                "vielen Werten im Abstand einer Saison, zweier Saisons und so "
                "weiter die Prognose gebildet wird."
            ),
            zh="跨季节的自回归阶数：预测由相隔一个、两个季节等的多少个值加权求和得到。",
        ),
        0,
        2,
        "Seasonal order P",
    )  # type: ignore
    seasonal_d: _order_field(
        "D",
        MultilingualString(
            en=(
                "How many times to difference the series one season apart. 1 "
                "removes a pattern that repeats at the same size every cycle."
            ),
            es=(
                "Cuantas veces diferenciar la serie con un desfase de una "
                "estacion. 1 elimina un patron que se repite con el mismo "
                "tamano en cada ciclo."
            ),
            pt=(
                "Quantas vezes diferenciar a serie com desfasamento de uma "
                "estacao. 1 remove um padrao que se repete com o mesmo tamanho "
                "em cada ciclo."
            ),
            de=(
                "Wie oft die Reihe im Abstand einer Saison differenziert wird. "
                "1 entfernt ein Muster, das sich in jedem Zyklus gleich stark "
                "wiederholt."
            ),
            zh=(
                "按一个季节的间隔对序列做几次差分。"
                "1 可去除每个周期以相同幅度重复的模式。"
            ),
        ),
        0,
        1,
        "Seasonal order D",
    )  # type: ignore
    seasonal_q: _order_field(
        "Q",
        MultilingualString(
            en="The moving average order across seasons.",
            es="El orden de media movil entre estaciones.",
            pt="A ordem de media movel entre estacoes.",
            de="Die Ordnung des gleitenden Mittels ueber Saisons hinweg.",
            zh="跨季节的移动平均阶数。",
        ),
        0,
        2,
        "Seasonal order Q",
    )  # type: ignore
    season_length: _order_field(
        "s",
        MultilingualString(
            en=(
                "How many observations make up one full cycle: 12 for monthly "
                "data repeating yearly, 7 for daily data repeating weekly. "
                "Leave it at 0 to model no season at all."
            ),
            es=(
                "Cuantas observaciones forman un ciclo completo: 12 para datos "
                "mensuales que se repiten cada ano, 7 para datos diarios que se "
                "repiten cada semana. Dejar en 0 para no modelar estacion."
            ),
            pt=(
                "Quantas observacoes formam um ciclo completo: 12 para dados "
                "mensais que se repetem a cada ano, 7 para dados diarios que se "
                "repetem a cada semana. Deixe em 0 para nao modelar estacao."
            ),
            de=(
                "Wie viele Beobachtungen einen vollen Zyklus bilden: 12 fuer "
                "monatliche Daten mit jaehrlicher Wiederholung, 7 fuer "
                "taegliche mit woechentlicher. Bei 0 wird keine Saison "
                "modelliert."
            ),
            zh=(
                "一个完整周期包含多少个观测值：月度数据按年重复为 12，"
                "日度数据按周重复为 7。保持为 0 表示不建模季节性。"
            ),
        ),
        0,
        12,
        "Season length",
    )  # type: ignore


class SARIMAX(ForecastingModel):
    """ARIMA with a seasonal part and explanatory variables.

    SARIMAX is ARIMA with two additions. The seasonal orders (``P``, ``D``,
    ``Q``, and the season length ``s``) repeat the autoregressive,
    differencing and moving average ideas at a lag of one whole cycle, which
    is what lets it model a pattern that comes back every December rather
    than one that depends only on last month. The ``X`` is for the exogenous
    variables: the series is regressed on them and what is left over is
    modelled as a seasonal ARIMA.

    Both additions are optional, which is why the model is offered for both
    forecasting tasks. Left at a season length of 0 and given only a date, it
    is an ordinary ARIMA. It is the model to reach for when a series has a
    seasonal pattern and something measurable driving it, which
    :class:`ARIMA` covers only halfway and :class:`ExponentialSmoothing` not
    at all.

    The orders are not chosen automatically, and there are seven of them. A
    reasonable starting point is a seasonal difference (``D = 1``) with the
    season length of the data when the pattern is obvious, leaving the rest
    as they are, and letting the DashAI optimizer search from there.

    References
    ----------
    - [1] https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html
    - [2] https://otexts.com/fpp3/seasonal-arima.html
    """

    SCHEMA = SARIMAXSchema
    COMPATIBLE_COMPONENTS = ["ForecastingTask", "ExogenousForecastingTask"]
    SUPPORTS_EXOGENOUS = True
    DESCRIPTION = MultilingualString(
        en=(
            "ARIMA extended with a seasonal part and with explanatory "
            "variables. Suits a series that repeats on a cycle, is driven by "
            "something measurable, or both."
        ),
        es=(
            "ARIMA ampliado con una parte estacional y con variables "
            "explicativas. Sirve para una serie que se repite en ciclos, que "
            "esta impulsada por algo medible, o ambas cosas."
        ),
        pt=(
            "ARIMA ampliado com uma parte sazonal e com variaveis "
            "explicativas. Serve para uma serie que se repete em ciclos, que e "
            "impulsionada por algo mensuravel, ou ambas."
        ),
        de=(
            "ARIMA, erweitert um einen saisonalen Teil und um erklaerende "
            "Variablen. Passt zu einer Reihe, die sich zyklisch wiederholt, von "
            "etwas Messbarem getrieben wird, oder beides."
        ),
        zh=(
            "在 ARIMA 基础上加入季节性部分和解释变量。"
            "适用于呈周期重复、受可测量因素驱动，或两者兼有的序列。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="SARIMAX", es="SARIMAX", pt="SARIMAX", de="SARIMAX", zh="SARIMAX"
    )

    def __init__(
        self,
        p: int = 1,
        d: int = 1,
        q: int = 0,
        seasonal_p: int = 0,
        seasonal_d: int = 0,
        seasonal_q: int = 0,
        season_length: int = 0,
        **kwargs,
    ):
        """Initialise the model with its orders.

        Parameters
        ----------
        p : int
            Autoregressive order.
        d : int
            Number of differences.
        q : int
            Moving average order.
        seasonal_p : int
            Seasonal autoregressive order.
        seasonal_d : int
            Number of seasonal differences.
        seasonal_q : int
            Seasonal moving average order.
        season_length : int
            Observations in one full cycle, or 0 for no seasonal part.
        **kwargs
            Ignored, accepted for consistency with the other models.
        """
        super().__init__(**kwargs)
        self.p = p
        self.d = d
        self.q = q
        self.seasonal_p = seasonal_p
        self.seasonal_d = seasonal_d
        self.seasonal_q = seasonal_q
        self.season_length = season_length
        self._result = None

    @property
    def _seasonal_order(self) -> tuple:
        """State the seasonal order the way statsmodels expects it.

        Returns
        -------
        tuple
            The four seasonal terms, all zero when no season was asked for.
        """
        if self.season_length < 2:
            return (0, 0, 0, 0)
        return (
            self.seasonal_p,
            self.seasonal_d,
            self.seasonal_q,
            self.season_length,
        )

    def train(
        self,
        x_train: "DashAIDataset",
        y_train: "DashAIDataset",
        x_validation: "DashAIDataset" = None,
        y_validation: "DashAIDataset" = None,
    ) -> "SARIMAX":
        """Fit the model to the series and its explanatory variables.

        Parameters
        ----------
        x_train : DashAIDataset
            The date column, and any numeric columns beside it, which are
            taken as explanatory variables. statsmodels is given the values in
            order and the spacing is assumed regular; the dates are kept so a
            later partition can be forecast at its own dates.
        y_train : DashAIDataset
            The series to forecast.
        x_validation : DashAIDataset, optional
            Unused.
        y_validation : DashAIDataset, optional
            Unused.

        Returns
        -------
        SARIMAX
            The fitted model.

        Raises
        ------
        ValueError
            If the series is too short for the requested orders, or shorter
            than two full cycles when a seasonal part was asked for.
        """
        import warnings

        from statsmodels.tsa.statespace.sarimax import SARIMAX as _SARIMAX

        series = self._series(y_train)
        needed = self.p + self.d + self.q
        if len(series) <= needed:
            raise ValueError(
                f"A SARIMAX({self.p},{self.d},{self.q}) needs more than "
                f"{needed} observations, but the series has {len(series)}."
            )

        seasonal_order = self._seasonal_order
        if seasonal_order[3] and len(series) < 2 * seasonal_order[3]:
            raise ValueError(
                f"A season of {seasonal_order[3]} needs at least "
                f"{2 * seasonal_order[3]} observations to be seen twice, but "
                f"the series has {len(series)}."
            )

        self._remember_exogenous(x_train)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._result = _SARIMAX(
                series,
                exog=self._exogenous_of(x_train),
                order=(self.p, self.d, self.q),
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False)

        self._history = list(series)
        self._remember_dates(x_train)
        self._fitted = True
        return self

    def _forecast(self, steps: int, exog: "np.ndarray | None" = None) -> "np.ndarray":
        """Forecast the next ``steps`` periods after the end of the history.

        Parameters
        ----------
        steps : int
            How many periods to forecast.
        exog : np.ndarray, optional
            The explanatory variables over those periods, when the model was
            fitted with any.

        Returns
        -------
        np.ndarray
            One value per period, in order.
        """
        return self._result.forecast(steps=steps, exog=exog)
