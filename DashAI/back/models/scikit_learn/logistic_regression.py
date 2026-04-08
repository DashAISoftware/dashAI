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
    """Schema that configures the Logistic Regression classifier.

    Logistic Regression is a supervised classification method that fits a linear
    decision boundary using a logistic (sigmoid) function. It supports binary and
    multiclass classification via the one-vs-rest strategy and optional L1, L2, or
    Elastic-Net regularisation. The underlying implementation is
    ``sklearn.linear_model.LogisticRegression``.
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
    """Logistic regression classifier with L1, L2, or Elastic-Net regularisation.

    Logistic Regression models the probability that a sample belongs to a given
    class by applying the logistic (sigmoid) function to a linear combination of
    input features. The decision boundary is linear in the feature space. For
    multiclass problems the model applies a one-vs-rest (OvR) strategy by default.

    Regularisation is controlled by the penalty (L1, L2, or Elastic-Net) and the
    inverse-strength parameter ``C``. The solver is selected automatically based on
    the chosen penalty. Key hyperparameters are ``penalty``, ``C``, ``tol``, and
    ``max_iter``. The implementation wraps scikit-learn's ``LogisticRegression``.

    References
    ----------
    - [1] Cox, D.R. (1958). "The regression analysis of binary sequences."
           Journal of the Royal Statistical Society, Series B, 20(2), 215-242.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
    """

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
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.  See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
