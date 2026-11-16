"""Forecasting by reduction to regression, with skforecast."""

from typing import TYPE_CHECKING, Any, Optional

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    none_type,
    schema_field,
    search_space,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.forecasting.single_series_forecasting_model import (
    EXOGENOUS_OPTIONAL,
    SEASON_FROM_FREQUENCY,
    SingleSeriesForecastingModel,
    use_exogenous_field,
)

if TYPE_CHECKING:
    import numpy as np

#: How many simulated paths bound a forecast, and the seed that draws them:
#: fixed, so the same model gives the same intervals every time.
N_BOOT = 250
RANDOM_STATE = 123

#: The fewest lags the default gives, for a series with no season or one
#: shorter than this.
MIN_DEFAULT_LAGS = 3


def sklearn_estimator(regressor: Any):
    """The plain scikit-learn estimator inside a DashAI regressor.

    skforecast clones the estimator it is handed, and scikit-learn's ``clone``
    rebuilds an estimator from ``get_params``. A DashAI regressor takes
    ``**kwargs``, which scikit-learn's ``_get_param_names`` cannot read, so
    ``get_params`` is empty and the clone silently falls back to the defaults:
    a forest configured with 7 trees would be fitted with 100. The estimator
    built here is the regressor's own scikit-learn class, instantiated with
    the values the regressor holds, so a clone of it keeps them.

    It is built on every fit rather than once, so it sees the values a search
    sets on the nested regressor for each trial.

    Parameters
    ----------
    regressor : object
        A DashAI regressor that is also a scikit-learn estimator, as the
        ``SklearnLikeRegressor`` models are. It is not modified.

    Returns
    -------
    sklearn.base.RegressorMixin
        An unfitted scikit-learn regressor with the same hyperparameters.

    Raises
    ------
    TypeError
        If no concrete scikit-learn regressor is among the regressor's
        classes: a torch model such as ``MLPRegression``, or a classifier.
    """
    import inspect

    from sklearn.base import RegressorMixin

    for cls in type(regressor).__mro__:
        if (
            cls.__module__.split(".")[0] == "sklearn"
            and cls is not RegressorMixin
            and issubclass(cls, RegressorMixin)
            and not inspect.isabstract(cls)
        ):
            names = cls._get_param_names()
            return cls(**{name: getattr(regressor, name) for name in names})
    raise TypeError(
        f"{type(regressor).__name__} is not a scikit-learn regressor: the "
        "reduction model regresses on the lags with one of the "
        "SklearnLikeRegressor models."
    )


class RecursiveRegressionForecasterSchema(BaseSchema):
    """Schema that configures the recursive regression forecaster."""

    regressor: schema_field(
        component_field(parent="SklearnLikeRegressor"),
        placeholder={"component": "LinearRegression", "params": {}},
        description=MultilingualString(
            en=(
                "The regression model that predicts the next value from the "
                "previous ones, along with its own configuration. A linear "
                "regression extends a trend; trees and forests cannot "
                "forecast past the values they were trained on."
            ),
            es=(
                "El modelo de regresión que predice el siguiente valor a "
                "partir de los anteriores, junto con su propia configuración. "
                "Una regresión lineal prolonga una tendencia; los árboles y "
                "los bosques no pueden pronosticar fuera de los valores con "
                "que se entrenaron."
            ),
            pt=(
                "O modelo de regressão que prevê o próximo valor a partir dos "
                "anteriores, junto com a sua própria configuração. Uma "
                "regressão linear prolonga uma tendência; árvores e florestas "
                "não conseguem prever fora dos valores com que foram treinadas."
            ),
            de=(
                "Das Regressionsmodell, das den nächsten Wert aus den "
                "vorherigen vorhersagt, samt seiner Konfiguration. Eine "
                "lineare Regression setzt einen Trend fort; Bäume und Wälder "
                "können nicht über die Werte hinaus prognostizieren, mit "
                "denen sie trainiert wurden."
            ),
            zh=(
                "根据之前的值预测下一个值的回归模型及其自身配置。"
                "线性回归可以延续趋势；树和森林无法预测超出训练值范围的结果。"
            ),
        ),
        alias=MultilingualString(
            en="Regressor", es="Regresor", pt="Regressor", de="Regressor", zh="回归器"
        ),
    )  # type: ignore
    lags: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en=(
                "How many past values the regressor reads to predict the next "
                "one. Left empty, one season of values, and at least "
                f"{MIN_DEFAULT_LAGS}."
            ),
            es=(
                "Cuántos valores pasados lee el regresor para predecir el "
                "siguiente. Vacío, una temporada de valores, y al menos "
                f"{MIN_DEFAULT_LAGS}."
            ),
            pt=(
                "Quantos valores passados o regressor lê para prever o "
                "próximo. Vazio, uma temporada de valores, e pelo menos "
                f"{MIN_DEFAULT_LAGS}."
            ),
            de=(
                "Wie viele vergangene Werte der Regressor liest, um den "
                "nächsten vorherzusagen. Leer: eine Saison von Werten, "
                f"mindestens {MIN_DEFAULT_LAGS}."
            ),
            zh=(
                "回归器读取多少个过去的值来预测下一个值。"
                f"留空时为一个季节的值，且至少为 {MIN_DEFAULT_LAGS}。"
            ),
        ),
        alias=MultilingualString(
            en="Lags", es="Rezagos", pt="Defasagens", de="Verzögerungen", zh="滞后数"
        ),
    )  # type: ignore
    season_length: search_space(
        none_type(int_field(ge=1)),
        fixed=None,
        low=1,
        high=12,
        description=MultilingualString(
            en=(
                "How many steps make up one season. In this model it only "
                "sets how many lags are read when Lags is left empty; it does "
                f"not model the seasonality. {SEASON_FROM_FREQUENCY.en}"
            ),
            es=(
                "Cuántos pasos forman una temporada. En este modelo solo "
                "decide cuántos rezagos se leen cuando Rezagos queda vacío; "
                f"no modela la estacionalidad. {SEASON_FROM_FREQUENCY.es}"
            ),
            pt=(
                "Quantos passos formam uma temporada. Neste modelo só define "
                "quantas defasagens são lidas quando Defasagens fica vazio; "
                f"não modela a sazonalidade. {SEASON_FROM_FREQUENCY.pt}"
            ),
            de=(
                "Wie viele Schritte eine Saison bilden. In diesem Modell legt "
                "sie nur fest, wie viele Verzögerungen gelesen werden, wenn "
                "Verzögerungen leer bleibt; die Saisonalität modelliert sie "
                f"nicht. {SEASON_FROM_FREQUENCY.de}"
            ),
            zh=(
                "一个季节包含多少步。在本模型中，它只决定滞后数留空时读取多少个滞后值，"
                f"并不对季节性建模。{SEASON_FROM_FREQUENCY.zh}"
            ),
        ),
        alias=MultilingualString(
            en="Season length",
            es="Largo de temporada",
            pt="Comprimento da temporada",
            de="Saisonlänge",
            zh="季节长度",
        ),
    )  # type: ignore
    differentiation: search_space(
        int_field(ge=0),
        fixed=0,
        low=0,
        high=2,
        description=MultilingualString(
            en=(
                "How many times to difference the series before regressing on "
                "it. Use 1 on a series with a trend: the regressor then "
                "predicts the changes, which a tree can do where it cannot "
                "predict values it has never seen. 0 leaves the series as it "
                "is."
            ),
            es=(
                "Cuántas veces diferenciar la serie antes de hacer la "
                "regresión. Usa 1 en una serie con tendencia: el regresor "
                "predice entonces los cambios, que un árbol sí puede predecir "
                "aunque no pueda predecir valores que nunca vio. 0 deja la "
                "serie como está."
            ),
            pt=(
                "Quantas vezes diferenciar a série antes da regressão. Use 1 "
                "numa série com tendência: o regressor passa a prever as "
                "variações, o que uma árvore consegue mesmo sem conseguir "
                "prever valores que nunca viu. 0 deixa a série como está."
            ),
            de=(
                "Wie oft die Reihe vor der Regression differenziert wird. "
                "Verwenden Sie 1 bei einer Reihe mit Trend: Der Regressor "
                "sagt dann die Änderungen vorher, was ein Baum kann, auch "
                "wenn er nie gesehene Werte nicht vorhersagen kann. 0 lässt "
                "die Reihe unverändert."
            ),
            zh=(
                "回归前对序列做几次差分。有趋势的序列用 1：回归器改为预测变化量，"
                "树模型虽然无法预测从未见过的值，却可以预测变化量。0 表示保持原序列。"
            ),
        ),
        alias=MultilingualString(
            en="Differencing",
            es="Diferenciación",
            pt="Diferenciação",
            de="Differenzierung",
            zh="差分",
        ),
    )  # type: ignore
    use_exogenous: use_exogenous_field()  # type: ignore


class RecursiveRegressionForecaster(SingleSeriesForecastingModel):
    """Forecast a series with a regression model that reads its own past.

    The reduction to regression: each value of the series is a target, and the
    ``lags`` values before it are its features. Any regressor can learn that
    table. To forecast several steps, the model predicts one step, appends
    the prediction to the history and predicts the next from it: the
    recursive strategy. Errors compound along the horizon, which is what the
    intervals show.

    The table and the recursion are skforecast's ``ForecasterRecursive``. The
    regressor is one of DashAI's scikit-learn regressors, chosen and
    configured in a nested form; skforecast is handed the plain scikit-learn
    estimator inside it (``sklearn_estimator``).

    Exogenous variables, when a run reads them, are features of each row next
    to the lags, and their future values are needed to forecast.

    Intervals come from bootstrapping the residuals of the training fit:
    ``N_BOOT`` paths are simulated by adding resampled residuals at every
    step of the recursion, and the bounds at each level are quantiles of those
    paths, so the 80% interval always lies within the 95% one. The residuals
    are signed, so a biased regressor can leave the point forecast outside
    its own interval.

    Known limits, stated in the description too:
    - a regressor that fits its training data closely, as trees do, leaves
      residuals near zero and intervals too narrow; the coverage of the
      backtest shows it;
    - with exogenous variables, the backtest measures the forecast with the
      future values that actually happened, so its error and coverage are
      optimistic when the future has to be estimated.

    References
    ----------
    - [1] https://skforecast.org/0.26.0/user_guides/autoregresive-forecaster
    - [2] https://otexts.com/fpp3/prediction-intervals.html
    """

    SCHEMA = RecursiveRegressionForecasterSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Turns forecasting into regression: a regression model learns "
            "each value from the previous ones and forecasts one step at a "
            "time. The intervals bootstrap the training errors, so with trees "
            "they come out too narrow; the backtest coverage shows it. With "
            "exogenous variables, the backtest error and coverage are "
            "optimistic."
        ),
        es=(
            "Convierte el pronóstico en una regresión: un modelo de regresión "
            "aprende cada valor a partir de los anteriores y pronostica un "
            "paso a la vez. Los intervalos remuestrean los errores del "
            "entrenamiento, así que con árboles salen demasiado angostos; la "
            "cobertura del backtest lo muestra. Con variables exógenas, el "
            "error y la cobertura del backtest son optimistas."
        ),
        pt=(
            "Transforma a previsão numa regressão: um modelo de regressão "
            "aprende cada valor a partir dos anteriores e prevê um passo de "
            "cada vez. Os intervalos reamostram os erros do treino, por isso "
            "com árvores saem estreitos demais; a cobertura do backtest "
            "mostra isso. Com variáveis exógenas, o erro e a cobertura do "
            "backtest são otimistas."
        ),
        de=(
            "Macht aus der Prognose eine Regression: Ein Regressionsmodell "
            "lernt jeden Wert aus den vorherigen und prognostiziert Schritt "
            "für Schritt. Die Intervalle ziehen die Trainingsfehler neu, "
            "daher fallen sie mit Bäumen zu schmal aus; die Abdeckung im "
            "Backtest zeigt es. Mit exogenen Variablen sind Fehler und "
            "Abdeckung des Backtests optimistisch."
        ),
        zh=(
            "把预测转化为回归：回归模型根据之前的值学习每个值，并逐步预测。"
            "区间通过对训练误差重抽样得到，因此使用树模型时区间偏窄，回测覆盖率会显示这一点。"
            "使用外生变量时，回测的误差和覆盖率偏乐观。"
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Recursive regression",
        es="Regresión recursiva",
        pt="Regressão recursiva",
        de="Rekursive Regression",
        zh="递归回归",
    )
    COLOR: str = "#AB47BC"
    ICON: str = "Insights"

    EXOGENOUS = EXOGENOUS_OPTIONAL
    SUPPORTS_INTERVALS = True

    def __init__(
        self,
        regressor: Any = None,
        lags: Optional[int] = None,
        season_length: int = 1,
        differentiation: int = 0,
        **kwargs,
    ):
        """Initialise the model with its regressor and its window.

        Parameters
        ----------
        regressor : SklearnLikeRegressor, optional
            The DashAI regressor, as ``ModelFactory`` builds it from the nested
            form. None gives a ``LinearRegression`` with its defaults.
        lags : int, optional
            How many past values each prediction reads. None means one
            season, and at least ``MIN_DEFAULT_LAGS``.
        season_length : int
            Steps per season. It only sets the default lags.
        differentiation : int
            How many times the series is differenced before the regression.
        **kwargs
            ``use_exogenous``, which the base keeps.

        Raises
        ------
        TypeError
            If the regressor is not one of the scikit-learn regressors.
        ValueError
            If ``season_length`` is None: the unit that builds the model fills
            an empty season from the frequency, so a None here is a wiring
            error, not a request for the default lags.
        """
        from DashAI.back.models.scikit_learn.sklearn_like_regressor import (
            SklearnLikeRegressor,
        )

        super().__init__(**kwargs)
        if season_length is None:
            raise ValueError(
                "season_length is None: the unit that builds the model reads an "
                "empty season from the series' frequency, so the model should "
                "never receive None."
            )
        if regressor is None:
            from DashAI.back.models.scikit_learn.linear_regression import (
                LinearRegression,
            )

            regressor = LinearRegression()
        if not isinstance(regressor, SklearnLikeRegressor):
            raise TypeError(
                f"{type(regressor).__name__} is not a scikit-learn regressor: "
                "the reduction model regresses on the lags with one of the "
                "SklearnLikeRegressor models."
            )
        self.regressor = regressor
        self.lags = lags
        self.season_length = season_length
        self.differentiation = differentiation
        self._forecaster = None
        self._train_length = 0

    def resolved_lags(self) -> int:
        """The lags each prediction reads: ``lags``, or one season, at least 3."""
        if self.lags is not None:
            return int(self.lags)
        return max(int(self.season_length), MIN_DEFAULT_LAGS)

    def _lags_source(self) -> str:
        """Where the lags came from, for a message: empty when given."""
        if self.lags is not None:
            return ""
        if int(self.season_length) < MIN_DEFAULT_LAGS:
            return " (the fewest the default gives, as Lags is left empty)"
        return " (one season, as Lags is left empty)"

    def fitted_estimator(self):
        """The scikit-learn estimator the last fit trained, or None unfitted."""
        return None if self._forecaster is None else self._forecaster.estimator

    def _fit(self, y: "np.ndarray", x: Optional[Any]) -> None:
        """Fit a recursive forecaster on the series and its exogenous rows.

        Parameters
        ----------
        y : np.ndarray
            The series, in time order.
        x : array-like, optional
            Exogenous variables, one row per step.

        Raises
        ------
        ValueError
            If the series leaves fewer training rows than values each row
            reads, plus one: the regression would have no single solution.
            Also if the regressor fails to fit, named in the message.
        """
        import numpy as np
        import pandas as pd
        from skforecast.recursive import ForecasterRecursive

        lags = self.resolved_lags()
        differentiation = int(self.differentiation or 0)
        n_exogenous = 0 if x is None else int(np.shape(x)[1])
        # Each row reads the lags and the exogenous values; with no more rows
        # than that (and the intercept), a linear regression is
        # underdetermined. It keeps the regression determined, nothing more:
        # with few rows the training residuals, and so the intervals, can
        # still come out narrow.
        values_per_row = lags + n_exogenous
        rows = len(y) - lags - differentiation
        if rows < values_per_row + 1:
            needed = lags + differentiation + values_per_row + 1
            exogenous = f" and {n_exogenous} exogenous variables" if n_exogenous else ""
            raise ValueError(
                f"A recursive regression with {lags} lags{self._lags_source()} "
                f"and differentiation {differentiation} needs at least {needed} "
                f"observations: {lags + differentiation} before its first "
                f"training row, and then one row more than the {values_per_row} "
                f"values each row reads (the lags{exogenous}), so that the "
                f"regression has a single solution. The history it is fitted on "
                f"has {len(y)} (in a backtest, the history before the first "
                "origin). Set fewer lags or less differencing, or use a longer "
                "history."
            )

        forecaster = ForecasterRecursive(
            estimator=sklearn_estimator(self.regressor),
            lags=lags,
            differentiation=differentiation or None,
        )
        try:
            forecaster.fit(
                y=pd.Series(y, index=pd.RangeIndex(len(y))),
                exog=self._exog(x, 0),
                store_in_sample_residuals=True,
                random_state=RANDOM_STATE,
                suppress_warnings=True,
            )
        except ValueError as error:
            # Only ValueError, which scikit-learn raises for data and
            # parameters it cannot fit (InvalidParameterError is one): a search
            # counts it as a trial that could not be fitted. Anything else is
            # wiring, and stays as it is.
            raise ValueError(
                f"Fitting {type(self.regressor).__name__} on {rows} rows of "
                f"{lags} lags failed: {error}"
            ) from error
        self._forecaster = forecaster
        self._train_length = len(y)

    def _forecast(self, h: int, x_future: Optional[Any]) -> "np.ndarray":
        """Forecast the next ``h`` steps, one at a time.

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
        return self._forecaster.predict(
            steps=h,
            exog=self._exog(x_future, self._train_length),
            suppress_warnings=True,
        ).to_numpy()

    def _intervals(self, h: int, levels, x_future: Optional[Any]):
        """Bounds from bootstrapped paths of the recursion.

        One call simulates ``N_BOOT`` paths, adding a residual of the training
        fit, drawn at random, to every step before it feeds the next. The
        bounds of each level are quantiles of the same paths, so the 80%
        interval lies within the 95% one. The seed is fixed: the same model
        gives the same intervals.
        """
        import numpy as np

        paths = self._forecaster.predict_bootstrapping(
            steps=h,
            exog=self._exog(x_future, self._train_length),
            n_boot=N_BOOT,
            random_state=RANDOM_STATE,
            use_in_sample_residuals=True,
            use_binned_residuals=False,
            suppress_warnings=True,
        ).to_numpy()
        lower, upper = {}, {}
        for level in levels:
            tail = (100.0 - level) / 200.0
            lower[level] = np.quantile(paths, tail, axis=1)
            upper[level] = np.quantile(paths, 1.0 - tail, axis=1)
        return lower, upper

    @staticmethod
    def _exog(x: Optional[Any], start: int):
        """The exogenous rows as skforecast takes them, or None.

        skforecast wants them in a frame indexed by step, the training rows
        from 0 and the future ones from the step after the last observed: the
        model never sees a date.
        """
        if x is None:
            return None
        import numpy as np
        import pandas as pd

        values = np.asarray(x, dtype=float)
        return pd.DataFrame(
            values,
            index=pd.RangeIndex(start, start + len(values)),
            columns=[f"exog_{i}" for i in range(values.shape[1])],
        )
