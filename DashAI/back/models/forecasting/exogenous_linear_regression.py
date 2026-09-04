from typing import TYPE_CHECKING

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    optimizer_float_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel

if TYPE_CHECKING:
    import numpy as np

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ExogenousLinearRegressionSchema(BaseSchema):
    """Schema that configures the exogenous linear regression forecaster."""

    include_trend: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "Whether to add the period number as an extra variable, which "
                "lets the model fit a steady drift up or down that the "
                "explanatory variables do not account for."
            ),
            es=(
                "Si se agrega el numero de periodo como variable adicional, lo "
                "que permite al modelo ajustar una deriva sostenida hacia "
                "arriba o abajo que las variables explicativas no explican."
            ),
            pt=(
                "Se o numero do periodo e adicionado como variavel extra, o "
                "que permite ao modelo ajustar uma deriva sustentada para cima "
                "ou para baixo que as variaveis explicativas nao explicam."
            ),
            de=(
                "Ob die Periodennummer als zusaetzliche Variable aufgenommen "
                "wird, womit das Modell eine stetige Drift abbilden kann, die "
                "die erklaerenden Variablen nicht erfassen."
            ),
            zh="是否将期数作为额外变量加入，使模型能拟合解释变量无法说明的持续上升或下降趋势。",
        ),
        alias=MultilingualString(
            en="Include a time trend",
            es="Incluir tendencia temporal",
            pt="Incluir tendencia temporal",
            de="Zeittrend einbeziehen",
            zh="包含时间趋势",
        ),
    )  # type: ignore
    regularization: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=(
                "How hard to pull the coefficients towards zero, the ridge "
                "penalty. 0 is ordinary least squares. Raise it when the "
                "explanatory variables move together, which otherwise makes "
                "the coefficients large and unstable."
            ),
            es=(
                "Con cuanta fuerza se llevan los coeficientes hacia cero, la "
                "penalizacion ridge. 0 es minimos cuadrados ordinarios. "
                "Aumentarla cuando las variables explicativas se mueven "
                "juntas, lo que de otro modo vuelve los coeficientes grandes e "
                "inestables."
            ),
            pt=(
                "Com que forca os coeficientes sao puxados para zero, a "
                "penalizacao ridge. 0 e minimos quadrados ordinarios. Aumente "
                "quando as variaveis explicativas se movem juntas, o que de "
                "outro modo torna os coeficientes grandes e instaveis."
            ),
            de=(
                "Wie stark die Koeffizienten gegen null gezogen werden, die "
                "Ridge-Strafe. 0 ist die gewoehnliche Kleinste-Quadrate-"
                "Schaetzung. Erhoehen, wenn sich die erklaerenden Variablen "
                "gemeinsam bewegen, was die Koeffizienten sonst gross und "
                "instabil macht."
            ),
            zh=(
                "将系数向零收缩的强度，即 ridge 惩罚。0 表示普通最小二乘。"
                "当解释变量同向变动时应调高，否则系数会变得很大且不稳定。"
            ),
        ),
        alias=MultilingualString(
            en="Regularization",
            es="Regularizacion",
            pt="Regularizacao",
            de="Regularisierung",
            zh="正则化",
        ),
    )  # type: ignore


class ExogenousLinearRegression(ForecastingModel):
    """Forecast a series as a straight line in its explanatory variables.

    The series is regressed on the variables measured beside it, and the
    forecast for a future period is that fit read at the values the variables
    take there. Nothing carries over from one period to the next: this model
    has no memory of the series at all, only of how the series responds to the
    things that move it.

    That is exactly what makes it worth having next to :class:`ARIMA` and
    :class:`SARIMAX`. Those two model the series and treat the variables as a
    correction; this one does the opposite, so a large gap between their
    scores says whether the series is driven by its own momentum or by
    something outside it. It is also the one model here whose coefficients can
    be read directly as "one more unit of this changes the forecast by that".

    Because it looks nowhere but at the variables, it is offered for
    :class:`ExogenousForecastingTask` alone and cannot forecast from a date
    column on its own.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html
    - [2] https://otexts.com/fpp3/regression.html
    """

    SCHEMA = ExogenousLinearRegressionSchema
    COMPATIBLE_COMPONENTS = ["ExogenousForecastingTask"]
    SUPPORTS_EXOGENOUS = True
    DESCRIPTION = MultilingualString(
        en=(
            "Fits the series as a straight line in the variables measured "
            "beside it and reads the forecast off that line. Ignores the "
            "history of the series, so it says how much of it the variables "
            "explain on their own."
        ),
        es=(
            "Ajusta la serie como una recta en las variables medidas junto a "
            "ella y lee el pronostico sobre esa recta. Ignora la historia de "
            "la serie, por lo que indica cuanto explican las variables por si "
            "solas."
        ),
        pt=(
            "Ajusta a serie como uma reta nas variaveis medidas ao seu lado e "
            "le a previsao sobre essa reta. Ignora a historia da serie, pelo "
            "que indica quanto as variaveis explicam por si so."
        ),
        de=(
            "Passt die Reihe als Gerade in den daneben gemessenen Variablen an "
            "und liest die Prognose von dieser Geraden ab. Ignoriert die "
            "Vergangenheit der Reihe und zeigt damit, wie viel die Variablen "
            "allein erklaeren."
        ),
        zh=(
            "把序列拟合为与其一同测量的变量的线性函数，并据此读出预测值。"
            "不使用序列自身的历史，因此能说明这些变量单独解释了多少。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Exogenous Linear Regression",
        es="Regresion Lineal Exogena",
        pt="Regressao Linear Exogena",
        de="Exogene lineare Regression",
        zh="外生变量线性回归",
    )

    def __init__(
        self, include_trend: bool = True, regularization: float = 0.0, **kwargs
    ):
        """Initialise the model.

        Parameters
        ----------
        include_trend : bool
            Whether the period number joins the explanatory variables.
        regularization : float
            The ridge penalty, 0 for ordinary least squares.
        **kwargs
            Ignored, accepted for consistency with the other models.
        """
        super().__init__(**kwargs)
        self.include_trend = include_trend
        self.regularization = regularization
        self._model = None
        self._observations = 0

    def _design(self, exog: "np.ndarray", start: int) -> "np.ndarray":
        """Build the matrix the regression is fitted on or read at.

        Parameters
        ----------
        exog : np.ndarray
            The explanatory variables, one row per period.
        start : int
            The period number of the first row, counted from the start of
            training. The trend has to keep counting past the training data,
            otherwise a forecast would sit at the same point on the line as
            the first training row.

        Returns
        -------
        np.ndarray
            The variables, with the period number appended when a trend was
            asked for.
        """
        import numpy as np

        if not self.include_trend:
            return exog

        trend = np.arange(start, start + len(exog), dtype=float).reshape(-1, 1)
        return np.hstack([exog, trend])

    def train(
        self,
        x_train: "DashAIDataset",
        y_train: "DashAIDataset",
        x_validation: "DashAIDataset" = None,
        y_validation: "DashAIDataset" = None,
    ) -> "ExogenousLinearRegression":
        """Fit the line through the training periods.

        Parameters
        ----------
        x_train : DashAIDataset
            The date column and the numeric columns beside it, which are the
            explanatory variables. The dates are kept so a later partition can
            be forecast at its own dates.
        y_train : DashAIDataset
            The series to forecast.
        x_validation : DashAIDataset, optional
            Unused.
        y_validation : DashAIDataset, optional
            Unused.

        Returns
        -------
        ExogenousLinearRegression
            The fitted model.

        Raises
        ------
        ValueError
            If no explanatory variables were given, since the model has
            nothing else to forecast from.
        """
        from sklearn.linear_model import Ridge

        self._remember_exogenous(x_train)
        exog = self._exogenous_of(x_train)
        if exog is None:
            raise ValueError(
                "ExogenousLinearRegression forecasts from explanatory "
                "variables alone, but it was given only a date column. Use a "
                "model that reads the history of the series, such as ARIMA."
            )

        series = self._series(y_train)
        self._model = Ridge(alpha=self.regularization).fit(
            self._design(exog, start=1), series
        )

        self._history = list(series)
        self._observations = len(series)
        self._remember_dates(x_train)
        self._fitted = True
        return self

    def _forecast(self, steps: int, exog: "np.ndarray | None" = None) -> "np.ndarray":
        """Read the fitted line at the variables of the next ``steps`` periods.

        Parameters
        ----------
        steps : int
            How many periods to forecast.
        exog : np.ndarray, optional
            The explanatory variables over those periods, one row per step.

        Returns
        -------
        np.ndarray
            One value per period, in order.
        """
        return self._model.predict(
            self._design(exog[:steps], start=self._observations + 1)
        )
