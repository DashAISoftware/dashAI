from sklearn.linear_model import Ridge as _Ridge

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
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


class RidgeRegressionSchema(BaseSchema):
    """Schema that configures the Ridge Regression model.

    Ridge Regression is a linear regression method that adds an L2 (squared-norm)
    penalty on the coefficients to the ordinary least-squares objective, shrinking
    coefficients towards zero to reduce overfitting and handle collinearity. It is
    used for tabular regression tasks. The underlying implementation is
    ``sklearn.linear_model.Ridge``.
    """

    alpha: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "Regularization strength; must be a positive float. "
                "Larger values specify stronger regularization."
            ),
            es=(
                "Fuerza de regularización; debe ser un float positivo. "
                "Valores más grandes especifican una regularización más fuerte."
            ),
        ),
        alias=MultilingualString(en="Alpha", es="Alfa"),
    )  # type: ignore

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

    max_iter: schema_field(
        optimizer_int_field(ge=10),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 10,
            "upper_bound": 10000,
        },
        description=MultilingualString(
            en="Maximum number of iterations for conjugate gradient solver.",
            es=(
                "Número máximo de iteraciones para el "
                "solucionador de gradiente conjugado."
            ),
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore
    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.001,
            "lower_bound": 1e-5,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en="Precision of the solution.",
            es="Precisión de la solución.",
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
    )  # type: ignore
    solver: schema_field(
        enum_field(
            enum=["auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga"]
        ),
        placeholder="auto",
        description=MultilingualString(
            en=(
                "Solver to use in the computation. 'auto' chooses the "
                "solver automatically based on the type of data."
            ),
            es=(
                "Solucionador a usar en el cálculo. 'auto' elige el "
                "solucionador automáticamente basado en el tipo de datos."
            ),
        ),
        alias=MultilingualString(en="Solver", es="Solucionador"),
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
    random_state: schema_field(
        none_type(optimizer_int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo random number generator to use "
                "when shuffling the data. Pass an int for reproducible output across "
                "multiple function calls, or None to not set a specific seed."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios a usar "
                "al mezclar los datos. Pase un int para salida reproducible entre "
                "múltiples llamadas, o None para no establecer una semilla específica."
            ),
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore


class RidgeRegression(RegressionModel, SklearnLikeRegressor, _Ridge):
    """Ridge regression with L2 regularisation to reduce coefficient magnitude.

    Ridge Regression minimises the penalised least-squares objective
    ``||y - Xw||^2 + alpha * ||w||^2``, where ``alpha`` is the regularisation
    strength. The L2 penalty shrinks all coefficients towards zero but does not
    set any of them exactly to zero, making Ridge suitable for situations where
    many predictors contribute small effects or when features are highly collinear.

    The solver (``svd``, ``cholesky``, ``lsqr``, ``sparse_cg``, ``sag``,
    ``saga``, or ``auto``) is selected based on data characteristics. Key
    hyperparameters are ``alpha``, ``fit_intercept``, ``solver``, and ``tol``.
    The implementation wraps scikit-learn's ``Ridge``.

    References
    ----------
    - [1] Hoerl, A.E. & Kennard, R.W. (1970). "Ridge Regression: Biased
           Estimation for Nonorthogonal Problems." Technometrics, 12(1), 55-67.
           https://doi.org/10.1080/00401706.1970.10488634
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html
    """

    SCHEMA = RidgeRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Ridge Regression",
        es="Regresión Ridge",
    )
    DESCRIPTION: str = MultilingualString(
        en="Linear regression with L2 regularization.",
        es="Regresión lineal con regularización L2.",
    )
    COLOR: str = "#2196F3"
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
