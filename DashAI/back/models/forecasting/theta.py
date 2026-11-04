from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import (
    BaseSchema,
    F,
    Ne,
    Relevance,
    enum_field,
    float_field,
    int_field,
    schema_field,
    search_space,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    SingleSeriesForecastingModel,
)

if TYPE_CHECKING:
    import numpy as np

SEASONAL = ["none", "add", "mul"]

# statsmodels names the two ways of removing a season in full.
_METHOD = {"add": "additive", "mul": "multiplicative"}

# Below three observations statsmodels' ThetaModel cannot fit its trend line:
# two fail with an IndexError from inside it, and one gives bounds that do not
# mean anything.
MIN_OBSERVATIONS = 3


class ThetaSchema(BaseSchema):
    """Schema that configures the Theta model."""

    seasonal: schema_field(
        enum_field(SEASONAL),
        "none",
        description=MultilingualString(
            en=(
                "Whether to remove a repeating pattern before forecasting and "
                "put it back after. 'add' when the swing is about the same "
                "size each cycle, 'mul' when it grows with the level (needs "
                "positive values), 'none' for a series with no season."
            ),
            es=(
                "Si se quita un patrón que se repite antes de pronosticar y se "
                "vuelve a poner después. 'add' cuando la oscilación tiene un "
                "tamaño similar en cada ciclo, 'mul' cuando crece con el nivel "
                "(requiere valores positivos), 'none' para una serie sin "
                "estacionalidad."
            ),
            pt=(
                "Se um padrão que se repete é removido antes da previsão e "
                "recolocado depois. 'add' quando a oscilação tem tamanho "
                "semelhante em cada ciclo, 'mul' quando cresce com o nível "
                "(requer valores positivos), 'none' para uma série sem "
                "sazonalidade."
            ),
            de=(
                "Ob ein wiederkehrendes Muster vor der Prognose entfernt und "
                "danach wieder hinzugefügt wird. 'add', wenn der Ausschlag pro "
                "Zyklus etwa gleich groß ist, 'mul', wenn er mit dem Niveau "
                "wächst (erfordert positive Werte), 'none' für eine Reihe "
                "ohne Saison."
            ),
            zh=(
                "是否在预测前去除重复模式并在预测后加回。'add' 表示每个周期"
                "波动幅度相近，'mul' 表示波动随水平增长（需要正值），'none' "
                "表示没有季节性的序列。"
            ),
        ),
        alias=MultilingualString(
            en="Seasonal",
            es="Estacional",
            pt="Sazonal",
            de="Saisonal",
            zh="季节性",
        ),
    )  # type: ignore
    season_length: search_space(
        int_field(ge=1),
        fixed=1,
        low=2,
        high=12,
        description=MultilingualString(
            en=(
                "How many observations make up one full cycle: 12 for monthly "
                "data repeating yearly, 7 for daily data repeating weekly."
            ),
            es=(
                "Cuántas observaciones forman un ciclo completo: 12 para datos "
                "mensuales que se repiten cada año, 7 para datos diarios que se "
                "repiten cada semana."
            ),
            pt=(
                "Quantas observações formam um ciclo completo: 12 para dados "
                "mensais que se repetem a cada ano, 7 para dados diários que se "
                "repetem a cada semana."
            ),
            de=(
                "Wie viele Beobachtungen einen vollen Zyklus bilden: 12 für "
                "monatliche Daten mit jährlicher Wiederholung, 7 für "
                "tägliche mit wöchentlicher."
            ),
            zh=(
                "一个完整周期包含多少个观测值：月度数据按年重复为 12，"
                "日度数据按周重复为 7。"
            ),
        ),
        alias=MultilingualString(
            en="Season length",
            es="Longitud de estación",
            pt="Comprimento da estação",
            de="Saisonlänge",
            zh="季节长度",
        ),
    )  # type: ignore
    theta: search_space(
        float_field(ge=1.0),
        fixed=2.0,
        low=1.0,
        high=3.0,
        description=MultilingualString(
            en=(
                "How much of the long-term trend the forecast follows. 1 "
                "ignores the trend and forecasts a flat line from the recent "
                "level; 2, the classical method, follows half of it; larger "
                "values follow more of it."
            ),
            es=(
                "Cuánto de la tendencia de largo plazo sigue el pronóstico. 1 "
                "ignora la tendencia y pronostica una línea plana desde el "
                "nivel reciente; 2, el método clásico, sigue la mitad; valores "
                "mayores siguen más."
            ),
            pt=(
                "Quanto da tendência de longo prazo a previsão segue. 1 ignora "
                "a tendência e prevê uma linha plana a partir do nível "
                "recente; 2, o método clássico, segue metade dela; valores "
                "maiores seguem mais."
            ),
            de=(
                "Wie stark die Prognose dem langfristigen Trend folgt. 1 "
                "ignoriert den Trend und prognostiziert eine flache Linie ab "
                "dem jüngsten Niveau; 2, das klassische Verfahren, folgt ihm "
                "zur Hälfte; größere Werte folgen ihm stärker."
            ),
            zh=(
                "预测在多大程度上跟随长期趋势。1 忽略趋势，从近期水平预测一条"
                "水平线；2 为经典方法，跟随一半趋势；更大的值跟随更多。"
            ),
        ),
        alias=MultilingualString(
            en="Theta", es="Theta", pt="Theta", de="Theta", zh="Theta"
        ),
    )  # type: ignore

    # season_length is an optimizer field, so a rule cannot read its value
    # (see ExponentialSmoothingSchema); the check that a season needs a length
    # of at least 2 lives in __init__.
    rules = [
        Relevance(
            "season_length",
            when=Ne(F("seasonal"), "none"),
            effect="disable",
            reason=MultilingualString(
                en=(
                    "The season length is only used when a seasonal component "
                    "is selected."
                ),
                es=(
                    "La longitud de estación solo se usa cuando se elige un "
                    "componente estacional."
                ),
                pt=(
                    "O comprimento da estação só é usado quando há um "
                    "componente sazonal."
                ),
                de=(
                    "Die Saisonlänge wird nur bei gewählter saisonaler "
                    "Komponente verwendet."
                ),
                zh="季节长度仅在选择季节性成分时使用。",
            ),
        ),
    ]


class Theta(SingleSeriesForecastingModel):
    """Forecast by blending the long-term trend with the recent level.

    The Theta method splits the series into two lines. The first is a straight
    line fitted to the whole history, its long-term direction. The second
    keeps the history's short-term swings, amplified around that line. The
    straight line is extended into the future, the second line is forecast
    with simple exponential smoothing, and the two forecasts are combined.

    Hyndman and Billah showed that the result is simple exponential smoothing
    with a drift of half the slope of the straight line. That damped trend is
    why the method holds up so well: it follows the direction of a series
    without projecting all of it. It won the M3 forecasting competition and is
    a standard benchmark since.

    The ``theta`` parameter sets how much of the trend the forecast follows: 1
    gives no drift, 2 is the classical method, larger values follow more of
    the slope.

    A seasonal component is removed by classical decomposition before the
    fit and put back on the forecast. When one is selected it is always
    applied: statsmodels would otherwise run a test first and skip the season
    without a word when the test does not find it.

    It uses no exogenous variables and only follows a linear trend.

    References
    ----------
    - [1] https://www.statsmodels.org/stable/generated/statsmodels.tsa.forecasting.theta.ThetaModel.html
    - [2] https://otexts.com/fpp3/the-theta-method.html
    """

    SCHEMA = ThetaSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Blends the long-term trend of a series with its recent level, "
            "following half of the trend by default. Simple, hard to overfit, "
            "and a strong benchmark for series with a steady direction."
        ),
        es=(
            "Combina la tendencia de largo plazo de una serie con su nivel "
            "reciente, siguiendo por defecto la mitad de la tendencia. Simple, "
            "difícil de sobreajustar y una referencia sólida para series con "
            "una dirección sostenida."
        ),
        pt=(
            "Combina a tendência de longo prazo de uma série com seu nível "
            "recente, seguindo por padrão metade da tendência. Simples, "
            "difícil de sobreajustar e uma referência sólida para séries com "
            "uma direção sustentada."
        ),
        de=(
            "Verbindet den langfristigen Trend einer Reihe mit ihrem jüngsten "
            "Niveau und folgt standardmäßig der Hälfte des Trends. Einfach, "
            "schwer zu überanpassen und ein starker Vergleichsmaßstab für "
            "Reihen mit stetiger Richtung."
        ),
        zh=(
            "将序列的长期趋势与其近期水平相结合，默认跟随一半趋势。简单、"
            "不易过拟合，是方向稳定的序列的有力基准。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Theta",
        es="Método Theta",
        pt="Método Theta",
        de="Theta-Methode",
        zh="Theta 方法",
    )

    SUPPORTS_INTERVALS = True

    def __init__(
        self,
        seasonal: str = "none",
        season_length: int = 1,
        theta: float = 2.0,
        **kwargs,
    ):
        """Initialise the model with its seasonal component and theta.

        Parameters
        ----------
        seasonal : str
            One of ``"none"``, ``"add"`` or ``"mul"``.
        season_length : int
            Observations per full cycle, used only with a seasonal component.
        theta : float
            How much of the trend the forecast follows, at least 1.
        **kwargs
            Ignored, accepted for consistency with the other models.

        Raises
        ------
        ValueError
            If ``seasonal`` is not a supported value, a seasonal component was
            asked for without a season length above 1, or ``theta`` is below 1.
        """
        super().__init__(**kwargs)
        if seasonal not in SEASONAL:
            raise ValueError(f"'seasonal' must be one of {SEASONAL}, got '{seasonal}'.")
        if seasonal != "none" and season_length < 2:
            raise ValueError(
                "A seasonal component needs a season length of at least 2, got "
                f"{season_length}. A season of 1 would repeat every "
                "observation, which is not a season."
            )
        if theta < 1:
            raise ValueError(
                f"Theta has to be at least 1, got {theta}. Below 1 the "
                "forecast would lean against the trend."
            )

        self.seasonal = seasonal
        self.season_length = season_length
        self.theta = float(theta)
        self._result = None

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Fit the Theta model to the series.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        x : None
            The model uses no exogenous variables.

        Raises
        ------
        ValueError
            If the series is too short for the trend line or for two full
            seasons, or a multiplicative season meets a value that is not
            positive.
        """
        import warnings

        from statsmodels.tsa.forecasting.theta import ThetaModel

        if len(y) < MIN_OBSERVATIONS:
            raise ValueError(
                f"Theta needs at least {MIN_OBSERVATIONS} observations to fit "
                f"its trend line, but the series has {len(y)}."
            )
        seasonal = self.seasonal != "none"
        if seasonal and len(y) < 2 * self.season_length:
            raise ValueError(
                f"A seasonal component with a season of {self.season_length} "
                f"needs at least {2 * self.season_length} observations to see "
                f"the pattern twice, but the series has {len(y)}."
            )
        if self.seasonal == "mul" and (y <= 0).any():
            raise ValueError(
                "A multiplicative season needs every value to be positive, but "
                f"the series has {int((y <= 0).sum())} value(s) at or below "
                "zero. Use an additive season instead."
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._result = ThetaModel(
                y,
                period=self.season_length if seasonal else 1,
                deseasonalize=seasonal,
                use_test=False,
                method=_METHOD.get(self.seasonal, "additive"),
            ).fit()

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Forecast the next ``h`` steps after the end of the history.

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

        return np.asarray(self._result.forecast(h, theta=self.theta), dtype=float)

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Normal intervals with the h-step variance of simple exponential smoothing.

        The Theta method is simple exponential smoothing with drift, so its
        h-step variance is sigma^2 * (1 + (h - 1) * alpha^2), as for SES (fpp3
        §8.7). statsmodels' ``prediction_intervals`` squares ``alpha - 1``
        instead of ``alpha`` (``1 + (h - 1) * (1 + (alpha - 1)^2)``), so its
        bounds are too wide for any alpha below 1: on series simulated from
        the Theta model, its 80% intervals cover 90% to 98% of the values from
        the second step on.
        """
        import numpy as np

        alpha = float(self._result.params["alpha"])
        steps = np.arange(h, dtype=float)
        sd = np.sqrt(self._result.sigma2 * (1 + steps * alpha**2))
        return self._normal_bounds(self._forecast(h, None), sd, levels)
