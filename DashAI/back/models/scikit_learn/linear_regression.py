from sklearn.linear_model import LinearRegression as _LinearRegression

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    none_type,
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


class LinearRegressionSchema(BaseSchema):
    """Schema that configures the Ordinary Least-Squares Linear Regression model.

    Linear Regression fits a linear model by minimising the residual sum of squares
    between observed targets and predicted values. It is used for tabular regression
    tasks. The underlying implementation is
    ``sklearn.linear_model.LinearRegression``.
    """

    fit_intercept: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Whether to calculate the intercept for this model. "
                "If set to False, no intercept will be used in calculations "
                "(e.g., data is expected to be centered)."
            ),
            es=(
                "Si se debe calcular el intercepto para este modelo. "
                "Si se establece en False, no se usará intercepto en los cálculos "
                "(ej., se espera que los datos estén centrados)."
            ),
        ),
        alias=MultilingualString(en="Fit intercept", es="Ajustar intercepto"),
    )  # type: ignore

    copy_X: schema_field(  # noqa: N815
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="If True, X will be copied; else, it may be overwritten.",
            es="Si es True, X será copiado; si no, puede ser sobrescrito.",
        ),
        alias=MultilingualString(en="Copy X", es="Copiar X"),
    )  # type: ignore

    n_jobs: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The number of jobs to use for the computation. "
                "None means 1 job, while -1 means using all processors."
            ),
            es=(
                "El número de trabajos a usar para el cálculo. "
                "None significa 1 trabajo, mientras que -1 significa usar todos "
                "los procesadores."
            ),
        ),
        alias=MultilingualString(en="N jobs", es="N trabajos"),
    )  # type: ignore

    positive: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en="When set to True, forces the coefficients to be positive.",
            es="Cuando se establece en True, fuerza los coeficientes a ser positivos.",
        ),
        alias=MultilingualString(en="Positive", es="Positivo"),
    )  # type: ignore


class LinearRegression(RegressionModel, SklearnLikeRegressor, _LinearRegression):
    """Ordinary least-squares linear regression model.

    Linear Regression models the relationship between one or more input features and
    a continuous target by fitting a linear equation ``y = Xw + b``. The coefficients
    ``w`` and intercept ``b`` are estimated by minimising the residual sum of squares
    ``||y - Xw||^2``, which has a closed-form solution via the normal equations or
    can be computed via singular value decomposition.

    This model has no regularisation, so it can overfit when the number of features
    is large or predictors are highly collinear (consider ``RidgeRegression`` in those
    cases). Key hyperparameters are ``fit_intercept``, ``positive`` (constraint to
    non-negative coefficients), ``copy_X``, and ``n_jobs``. The implementation wraps
    scikit-learn's ``LinearRegression``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html
    """

    SCHEMA = LinearRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Linear Regression",
        es="Regresión Lineal",
    )
    DESCRIPTION: str = MultilingualString(
        en="Ordinary least squares linear regression.",
        es="Regresión lineal de mínimos cuadrados ordinarios.",
    )
    COLOR: str = "#3F51B5"
    ICON: str = "ShowChart"

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
