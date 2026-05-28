from sklearn.ensemble import AdaBoostRegressor as _AdaBoostRegressor

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class AdaBoostRegressionSchema(BaseSchema):
    """Schema that configures the AdaBoost Regressor.

    AdaBoost Regressor fits a sequence of weak regressors on re-weighted versions
    of the training data, concentrating on samples with high residuals. The
    underlying implementation is ``sklearn.ensemble.AdaBoostRegressor``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 50,
            "lower_bound": 10,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en=(
                "The maximum number of estimators at which boosting is terminated. "
                "In case of perfect fit, the learning procedure stops early."
            ),
            es=(
                "El número máximo de estimadores en el que se termina el boosting. "
                "En caso de ajuste perfecto, el procedimiento se detiene antes."
            ),
            pt=(
                "O número máximo de estimadores em que o boosting é encerrado. "
                "Em caso de ajuste perfeito, o procedimento é interrompido antes."
            ),
            de=(
                "Die maximale Anzahl von Schätzern, bei der das Boosting beendet wird. "
                "Bei perfekter Anpassung wird das Lernverfahren vorzeitig gestoppt."
            ),
        ),
        alias=MultilingualString(
            en="N estimators",
            es="N estimadores",
            pt="N estimadores",
            de="Anzahl Schätzer",
        ),
    )  # type: ignore

    learning_rate: schema_field(
        optimizer_float_field(ge=0.01),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.01,
            "upper_bound": 2.0,
        },
        description=MultilingualString(
            en=(
                "Weight applied to each regressor at each boosting iteration. "
                "There is a trade-off between learning_rate and n_estimators."
            ),
            es=(
                "Peso aplicado a cada regresor en cada iteración de boosting. "
                "Existe un trade-off entre learning_rate y n_estimators."
            ),
            pt=(
                "Peso aplicado a cada regressor em cada iteração de boosting. "
                "Existe um trade-off entre learning_rate e n_estimators."
            ),
            de=(
                "Gewicht, das bei jeder Boosting-Iteration auf jeden Regressor "
                "angewendet wird. "
                "Es gibt einen Trade-off zwischen Lernrate und Anzahl Schätzer."
            ),
        ),
        alias=MultilingualString(
            en="Learning rate",
            es="Tasa de aprendizaje",
            pt="Taxa de aprendizado",
            de="Lernrate",
        ),
    )  # type: ignore

    loss: schema_field(
        enum_field(enum=["linear", "square", "exponential"]),
        placeholder="linear",
        description=MultilingualString(
            en=(
                "The loss function to use when updating the weights after each "
                "boosting iteration."
            ),
            es=(
                "La función de pérdida a usar al actualizar los pesos después de "
                "cada iteración de boosting."
            ),
            pt=(
                "A função de perda a usar ao atualizar os pesos após cada "
                "iteração de boosting."
            ),
            de=(
                "Die Verlustfunktion, die beim Aktualisieren der Gewichte nach jeder "
                "Boosting-Iteration verwendet wird."
            ),
        ),
        alias=MultilingualString(en="Loss", es="Pérdida", pt="Perda", de="Verlust"),
    )  # type: ignore

    random_state: schema_field(
        none_type(optimizer_int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo-random number generator. Pass an int for "
                "reproducible output, or None to not set a specific seed."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios. Pase un int "
                "para salida reproducible, o None para no fijar una semilla."
            ),
            pt=(
                "A semente do gerador de números pseudoaleatórios. Passe um int para "
                "saída reproduzível, ou None para não definir uma semente específica."
            ),
            de=(
                "Der Seed des Pseudozufallszahlengenerators. Übergeben Sie eine ganze "
                "Zahl für "
                "reproduzierbare Ausgaben oder None, um keinen bestimmten Seed "
                "festzulegen."
            ),
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
        ),
    )  # type: ignore


class AdaBoostRegression(RegressionModel, SklearnLikeRegressor, _AdaBoostRegressor):
    """AdaBoost regressor that focuses on samples with high prediction errors.

    AdaBoostRegressor fits weak regressors (decision stumps by default) sequentially
    on re-weighted training data, assigning higher weights to samples with larger
    errors. The final prediction is a weighted median of all weak regressors.

    Key hyperparameters include ``n_estimators``, ``learning_rate``, and ``loss``.
    The implementation wraps scikit-learn's ``AdaBoostRegressor``.

    References
    ----------
    - [1] Drucker, H. (1997). "Improving Regressors using Boosting Techniques."
           ICML, 107-115.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.AdaBoostRegressor.html
    """

    SCHEMA = AdaBoostRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="AdaBoost Regression",
        es="Regresión AdaBoost",
        pt="Regressão AdaBoost",
        de="AdaBoost Regression",
    )
    DESCRIPTION: str = MultilingualString(
        en="Adaptive boosting that focuses on samples with large residuals.",
        es="Boosting adaptivo que se enfoca en muestras con grandes residuos.",
        pt="Boosting adaptivo que se concentra em amostras com grandes resíduos.",
        de=(
            "Adaptives Boosting, das sich auf Stichproben mit großen Residuen "
            "konzentriert."
        ),
    )
    COLOR: str = "#FFA726"
    ICON: str = "Bolt"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
