from sklearn.ensemble import (
    HistGradientBoostingRegressor as _HistGradientBoostingRegressor,
)

from DashAI.back.core.schema_fields import (
    BaseSchema,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class HistGradientBoostingRegressionSchema(BaseSchema):
    """Schema that configures the Histogram-based Gradient Boosting Regressor.

    Histogram-based Gradient Boosting is a fast sequential ensemble method that
    bins features into histograms before building each tree, greatly reducing cost
    on large datasets. The underlying implementation is
    ``sklearn.ensemble.HistGradientBoostingRegressor``.
    """

    learning_rate: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.1,
            "lower_bound": 0.01,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "The learning rate (shrinkage). Used as a multiplicative factor "
                "for leaf values. Use 1 for no shrinkage."
            ),
            es=(
                "La tasa de aprendizaje (shrinkage). Se usa como factor multiplicativo "
                "para los valores de las hojas. Use 1 para no aplicar shrinkage."
            ),
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
    )  # type: ignore

    max_iter: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 50,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en="Maximum number of iterations (trees) of the boosting process.",
            es="Número máximo de iteraciones (árboles) del proceso de boosting.",
        ),
        alias=MultilingualString(en="Max iterations", es="Máximas iteraciones"),
    )  # type: ignore

    max_depth: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=("Maximum depth of each tree. If None, depth is not constrained."),
            es=(
                "Profundidad máxima de cada árbol. Si es None, la profundidad "
                "no está restringida."
            ),
        ),
        alias=MultilingualString(en="Max depth", es="Profundidad máxima"),
    )  # type: ignore

    max_leaf_nodes: schema_field(
        union_type(optimizer_int_field(ge=2), none_type(int)),
        placeholder=31,
        description=MultilingualString(
            en=(
                "Maximum number of leaves for each tree. Must be strictly greater "
                "than 1. If None, no maximum limit."
            ),
            es=(
                "Número máximo de hojas para cada árbol. Debe ser estrictamente "
                "mayor que 1. Si es None, no hay límite."
            ),
        ),
        alias=MultilingualString(en="Max leaf nodes", es="Máximos nodos hoja"),
    )  # type: ignore

    min_samples_leaf: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 20,
            "lower_bound": 1,
            "upper_bound": 100,
        },
        description=MultilingualString(
            en="Minimum number of samples required to be at a leaf node.",
            es="Número mínimo de muestras requeridas para estar en una hoja.",
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
        ),
    )  # type: ignore

    l2_regularization: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="The L2 regularisation parameter. Use 0 for no regularisation.",
            es=(
                "El parámetro de regularización L2. "
                "Use 0 para no aplicar regularización."
            ),
        ),
        alias=MultilingualString(en="L2 regularization", es="Regularización L2"),
    )  # type: ignore


class HistGradientBoostingRegression(
    RegressionModel, SklearnLikeRegressor, _HistGradientBoostingRegressor
):
    """Histogram-based gradient boosting regressor for large datasets.

    This regressor discretises features into integer-valued bins before tree
    construction. The histogram representation reduces candidate split points and
    memory footprint, enabling efficient training on datasets with tens of thousands
    of samples or more. It natively supports missing values and is inspired by
    LightGBM.

    Key hyperparameters include ``learning_rate``, ``max_iter``, ``max_depth``,
    ``max_leaf_nodes``, ``min_samples_leaf``, and ``l2_regularization``. The
    implementation wraps scikit-learn's ``HistGradientBoostingRegressor``.

    References
    ----------
    - [1] Ke, G. et al. (2017). "LightGBM: A Highly Efficient Gradient Boosting
           Decision Tree." NeurIPS 30.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
    """

    SCHEMA = HistGradientBoostingRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Histogram Gradient Boosting Regression",
        es="Regresión Gradient Boosting con Histogramas",
    )
    DESCRIPTION: str = MultilingualString(
        en="Fast gradient boosting regression using histogram-based algorithms.",
        es=(
            "Regresión gradient boosting rápida usando algoritmos basados "
            "en histogramas."
        ),
    )
    COLOR: str = "#9575CD"
    ICON: str = "RocketLaunch"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
