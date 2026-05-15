from sklearn.linear_model import Lasso as _Lasso

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class LassoRegressionSchema(BaseSchema):
    """Schema that configures the Lasso Regression model.

    Lasso (Least Absolute Shrinkage and Selection Operator) adds an L1 penalty on
    the absolute values of coefficients, driving some of them exactly to zero,
    which performs implicit feature selection. The underlying implementation is
    ``sklearn.linear_model.Lasso``.
    """

    alpha: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.0001,
            "upper_bound": 10.0,
        },
        description=MultilingualString(
            en=(
                "Regularisation strength. Larger values specify stronger "
                "regularisation. alpha=0 is equivalent to OLS."
            ),
            es=(
                "Fuerza de regularización. Valores más grandes especifican "
                "regularización más fuerte. alpha=0 es equivalente a MCO."
            ),
        ),
        alias=MultilingualString(en="Alpha", es="Alfa"),
    )  # type: ignore

    fit_intercept: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Whether to calculate the intercept for this model. If False, "
                "the data is expected to be already centred."
            ),
            es=(
                "Si se calcula el intercepto para este modelo. Si es False, "
                "se espera que los datos ya estén centrados."
            ),
        ),
        alias=MultilingualString(en="Fit intercept", es="Ajustar intercepto"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=100),
        placeholder={
            "optimize": False,
            "fixed_value": 1000,
            "lower_bound": 100,
            "upper_bound": 10000,
        },
        description=MultilingualString(
            en="The maximum number of iterations.",
            es="El número máximo de iteraciones.",
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore

    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1e-4,
            "lower_bound": 1e-6,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en="The tolerance for the optimisation.",
            es="La tolerancia para la optimización.",
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
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
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore


class LassoRegression(RegressionModel, SklearnLikeRegressor, _Lasso):
    """Lasso regression with L1 regularisation for sparse coefficient solutions.

    Lasso minimises the OLS objective plus an L1 penalty
    ``||y - Xw||^2 / (2*n) + alpha * ||w||_1``. The L1 term sets many
    coefficients exactly to zero, performing automatic feature selection. Lasso is
    particularly useful when there are many features but only a few are expected to
    be relevant.

    Key hyperparameters include ``alpha``, ``fit_intercept``, ``max_iter``, and
    ``tol``. The implementation wraps scikit-learn's ``Lasso``.

    References
    ----------
    - [1] Tibshirani, R. (1996). "Regression Shrinkage and Selection via the Lasso."
           Journal of the Royal Statistical Society B, 58(1), 267-288.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Lasso.html
    """

    SCHEMA = LassoRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Lasso Regression",
        es="Regresión Lasso",
    )
    DESCRIPTION: str = MultilingualString(
        en="Linear regression with L1 regularisation for feature selection.",
        es="Regresión lineal con regularización L1 para selección de características.",
    )
    COLOR: str = "#29B6F6"
    ICON: str = "SelectAll"
    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
