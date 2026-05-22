from sklearn.svm import SVR as _SVR

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
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


class SVRSchema(BaseSchema):
    """Schema that configures the Support Vector Regressor.

    SVR (Support Vector Regression) finds a function that deviates from the
    observed targets by at most ``epsilon`` while being as flat as possible. It
    uses kernel functions to handle non-linear relationships. The underlying
    implementation is ``sklearn.svm.SVR``.
    """

    kernel: schema_field(
        enum_field(enum=["rbf", "linear", "poly", "sigmoid"]),
        placeholder="rbf",
        description=MultilingualString(
            en=(
                "Specifies the kernel type to be used in the algorithm. "
                "'rbf' is the default radial basis function."
            ),
            es=(
                "Especifica el tipo de kernel a usar. "
                "'rbf' es la función de base radial predeterminada."
            ),
            pt=(
                "Especifica o tipo de kernel a usar. "
                "'rbf' é a função de base radial padrão."
            ),
        ),
        alias=MultilingualString(en="Kernel", es="Kernel", pt="Kernel"),
    )  # type: ignore

    C: schema_field(  # noqa: N815
        optimizer_float_field(ge=1e-4),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.01,
            "upper_bound": 100.0,
        },
        description=MultilingualString(
            en=(
                "Regularisation parameter. Inversely proportional to the "
                "strength of the regularisation."
            ),
            es=(
                "Parámetro de regularización. Inversamente proporcional a la "
                "fuerza de la regularización."
            ),
            pt=(
                "Parâmetro de regularização. Inversamente proporcional à "
                "força da regularização."
            ),
        ),
        alias=MultilingualString(en="C", es="C", pt="C"),
    )  # type: ignore

    epsilon: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.1,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Specifies the epsilon-tube within which no penalty is associated "
                "in the training loss function."
            ),
            es=(
                "Especifica el tubo epsilon dentro del cual no se asocia penalización "
                "en la función de pérdida de entrenamiento."
            ),
            pt=(
                "Especifica o tubo epsilon dentro do qual nenhuma penalização é "
                "associada na função de perda de treinamento."
            ),
        ),
        alias=MultilingualString(en="Epsilon", es="Épsilon", pt="Épsilon"),
    )  # type: ignore

    gamma: schema_field(
        enum_field(enum=["scale", "auto"]),
        placeholder="scale",
        description=MultilingualString(
            en=(
                "Kernel coefficient for 'rbf', 'poly' and 'sigmoid'. "
                "'scale' uses 1/(n_features * X.var()); 'auto' uses 1/n_features."
            ),
            es=(
                "Coeficiente del kernel para 'rbf', 'poly' y 'sigmoid'. "
                "'scale' usa 1/(n_features * X.var()); 'auto' usa 1/n_features."
            ),
            pt=(
                "Coeficiente do kernel para 'rbf', 'poly' e 'sigmoid'. "
                "'scale' usa 1/(n_features * X.var()); 'auto' usa 1/n_features."
            ),
        ),
        alias=MultilingualString(en="Gamma", es="Gamma", pt="Gamma"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=-1),
        placeholder={
            "optimize": False,
            "fixed_value": -1,
            "lower_bound": 100,
            "upper_bound": 10000,
        },
        description=MultilingualString(
            en=("Hard limit on iterations within solver. -1 means no limit."),
            es=(
                "Límite en iteraciones dentro del solucionador. "
                "-1 significa sin límite."
            ),
            pt=("Limite de iterações dentro do solucionador. -1 significa sem limite."),
        ),
        alias=MultilingualString(
            en="Max iterations", es="Máximas iteraciones", pt="Iterações máximas"
        ),
    )  # type: ignore


class SVR(RegressionModel, SklearnLikeRegressor, _SVR):
    """Support Vector Regressor using kernel-based function estimation.

    SVR seeks a function that deviates from the targets by at most ``epsilon``
    (the insensitive tube) while maintaining flatness (controlled by ``C``).
    Kernel functions allow SVR to capture non-linear relationships. The RBF kernel
    is effective in many practical scenarios.

    Key hyperparameters include ``kernel``, ``C``, ``epsilon``, ``gamma``, and
    ``max_iter``. The implementation wraps scikit-learn's ``SVR``.

    References
    ----------
    - [1] Vapnik, V.N. (1995). The Nature of Statistical Learning Theory. Springer.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVR.html
    """

    SCHEMA = SVRSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Support Vector Regression",
        es="Regresión de Vectores de Soporte",
        pt="Regressão de Vetores de Suporte",
    )
    DESCRIPTION: str = MultilingualString(
        en="Kernel-based SVR that finds a function within an epsilon-insensitive tube.",
        es=(
            "SVR basado en kernel que encuentra una función dentro de un tubo "
            "insensible a épsilon."
        ),
        pt=(
            "SVR baseado em kernel que encontra uma função dentro de um tubo "
            "insensível a épsilon."
        ),
    )
    COLOR: str = "#EF5350"
    ICON: str = "ControlPoint"
    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
