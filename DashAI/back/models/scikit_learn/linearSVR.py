from sklearn.svm import LinearSVR as _LinearSVR

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class LinearSVRSchema(BaseSchema):
    """Support Vector Regression (SVR) using a linear kernel."""

    epsilon: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 1,
        },
        description=MultilingualString(
            en=(
                "Epsilon parameter that specifies the epsilon-tube within "
                "which no penalty is associated."
            ),
            es=(
                "Parámetro epsilon que especifica el tubo-epsilon dentro del cual "
                "no se asocia ninguna penalización."
            ),
        ),
        alias=MultilingualString(en="Epsilon", es="Epsilon"),
    )  # type: ignore

    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0001,
            "lower_bound": 1e-5,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en="Tolerance for stopping criterion.",
            es="Tolerancia para el criterio de detención.",
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
    )  # type: ignore

    C: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "Regularization parameter. The strength of the regularization "
                "is inversely proportional to C."
            ),
            es=(
                "Parámetro de regularización. La fuerza de la regularización "
                "es inversamente proporcional a C."
            ),
        ),
        alias=MultilingualString(en="C", es="C"),
    )  # type: ignore

    loss: schema_field(
        enum_field(enum=["epsilon_insensitive", "squared_epsilon_insensitive"]),
        placeholder="epsilon_insensitive",
        description=MultilingualString(
            en=(
                "Specifies the loss function. 'epsilon_insensitive' is "
                "the standard SVR loss."
            ),
            es=(
                "Especifica la función de pérdida. 'epsilon_insensitive' es "
                "la pérdida estándar de SVR."
            ),
        ),
        alias=MultilingualString(en="Loss", es="Pérdida"),
    )  # type: ignore

    fit_intercept: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to calculate the intercept for this model.",
            es="Si se debe calcular el intercepto para este modelo.",
        ),
        alias=MultilingualString(en="Fit intercept", es="Ajustar intercepto"),
    )  # type: ignore

    intercept_scaling: schema_field(
        optimizer_float_field(ge=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "When fit_intercept is True, instance vector x becomes "
                "[x, self.intercept_scaling] in the primal problem."
            ),
            es=(
                "Cuando fit_intercept es True, el vector de instancia x se convierte "
                "en [x, self.intercept_scaling] en el problema primal."
            ),
        ),
        alias=MultilingualString(en="Intercept scaling", es="Escala del intercepto"),
    )  # type: ignore

    dual: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Select the algorithm to either solve the dual or primal "
                "optimization problem."
            ),
            es=(
                "Selecciona el algoritmo para resolver el problema de optimización "
                "dual o primal."
            ),
        ),
        alias=MultilingualString(en="Dual", es="Dual"),
    )  # type: ignore

    verbose: schema_field(
        optimizer_int_field(ge=0),
        placeholder={
            "optimize": False,
            "fixed_value": 0,
            "lower_bound": 0,
            "upper_bound": 100,
        },
        description=MultilingualString(
            en=(
                "Enable verbose output. Note that this setting takes "
                "advantage of a per-process runtime setting in libsvm."
            ),
            es=(
                "Habilitar salida detallada. Note que esta configuración aprovecha "
                "una configuración de tiempo de ejecución por proceso en libsvm."
            ),
        ),
        alias=MultilingualString(en="Verbose", es="Verboso"),
    )  # type: ignore

    random_state: schema_field(
        union_type(optimizer_int_field(ge=0), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo-random number generator to use "
                "when shuffling the data."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios a usar "
                "al mezclar los datos."
            ),
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1000,
            "lower_bound": 100,
            "upper_bound": 10000,
        },
        description=MultilingualString(
            en="The maximum number of iterations to be run.",
            es="El número máximo de iteraciones a ejecutar.",
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore


class LinearSVR(RegressionModel, SklearnLikeRegressor, _LinearSVR):
    """Scikit-learn's Linear Support Vector Regression (LinearSVR)
    wrapper for DashAI.
    """

    SCHEMA = LinearSVRSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Linear Support Vector Regression",
        es="Regresión de Vectores de Soporte Lineal",
    )
    DESCRIPTION: str = MultilingualString(
        en="Support Vector Regression with linear kernel.",
        es="Regresión de Vectores de Soporte con kernel lineal.",
    )
    COLOR: str = "#2196F3"
    ICON: str = "Timeline"

    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
