from sklearn.linear_model import LogisticRegression as _LogisticRegression

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class LogisticRegressionSchema(BaseSchema):
    """Logistic Regression is a supervised classification method that uses a linear
    model plus a a logistic funcion to predict binary outcomes (it can be configured
    as multiclass via the one-vs-rest strategy).
    """

    penalty: schema_field(
        enum_field(enum=["l2", "l1", "elasticnet"]),
        placeholder="l2",
        description=MultilingualString(
            en="Specify the norm of the penalty",
            es="Especifica la norma de la penalización",
        ),
        alias=MultilingualString(en="Penalty", es="Penalización"),
    )  # type: ignore
    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 5.0,
        },
        description=MultilingualString(
            en="Tolerance for stopping criteria.",
            es="Tolerancia para el criterio de detención.",
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
    )  # type: ignore
    C: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 7.0,
        },
        description=MultilingualString(
            en=(
                "Inverse of regularization strength, smaller values specify stronger "
                "regularization. Must be a positive number."
            ),
            es=(
                "Inverso de la fuerza de regularización, valores más pequeños "
                "especifican una regularización más fuerte. Debe ser un número "
                "positivo."
            ),
        ),
        alias=MultilingualString(en="C", es="C"),
    )  # type: ignore
    max_iter: schema_field(
        optimizer_int_field(ge=50),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 50,
            "upper_bound": 250,
        },
        description=MultilingualString(
            en=("Maximum number of iterations taken for the solvers to converge."),
            es=("Número máximo de iteraciones para que los solucionadores converjan."),
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore


class LogisticRegression(
    TabularClassificationModel, SklearnLikeClassifier, _LogisticRegression
):
    """Scikit-learn's Logistic Regression wrapper for DashAI."""

    SCHEMA = LogisticRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Logistic Regression",
        es="Regresión Logística",
    )
    DESCRIPTION: str = MultilingualString(
        en="Linear model for classification using logistic function.",
        es="Modelo lineal para clasificación usando la función logística.",
    )
    COLOR: str = "#64B5F6"
    ICON: str = "TrendingUp"

    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
