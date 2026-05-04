from sklearn.tree import DecisionTreeRegressor as _DecisionTreeRegressor

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


class DecisionTreeRegressionSchema(BaseSchema):
    """Schema that configures the Decision Tree Regressor.

    The Decision Tree Regressor builds a tree by recursively splitting the feature
    space to minimise MSE (or MAE) at each node. The underlying implementation is
    ``sklearn.tree.DecisionTreeRegressor``.
    """

    max_depth: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The maximum depth of the tree. If None, nodes are expanded until "
                "all leaves are pure or fewer than min_samples_split samples remain."
            ),
            es=(
                "La profundidad máxima del árbol. Si es None, los nodos se expanden "
                "hasta que todas las hojas sean puras o queden menos de "
                "min_samples_split muestras."
            ),
        ),
        alias=MultilingualString(en="Max depth", es="Profundidad máxima"),
    )  # type: ignore

    min_samples_split: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 2,
            "lower_bound": 2,
            "upper_bound": 20,
        },
        description=MultilingualString(
            en="Minimum number of samples required to split an internal node.",
            es="Número mínimo de muestras requeridas para dividir un nodo interno.",
        ),
        alias=MultilingualString(
            en="Min samples split", es="Mínimas muestras de división"
        ),
    )  # type: ignore

    min_samples_leaf: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 20,
        },
        description=MultilingualString(
            en="Minimum number of samples required to be at a leaf node.",
            es="Número mínimo de muestras requeridas para estar en una hoja.",
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
        ),
    )  # type: ignore

    max_leaf_nodes: schema_field(
        union_type(optimizer_int_field(ge=2), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Grow a tree with at most max_leaf_nodes in best-first fashion. "
                "If None, unlimited leaf nodes."
            ),
            es=(
                "Crecer un árbol con a lo sumo max_leaf_nodes de manera best-first. "
                "Si es None, nodos hoja ilimitados."
            ),
        ),
        alias=MultilingualString(en="Max leaf nodes", es="Máximos nodos hoja"),
    )  # type: ignore

    min_impurity_decrease: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 0.5,
        },
        description=MultilingualString(
            en=(
                "A node is split if the split induces a decrease of the impurity "
                "greater than or equal to this value."
            ),
            es=(
                "Un nodo se divide si la división induce una disminución de la "
                "impureza mayor o igual a este valor."
            ),
        ),
        alias=MultilingualString(
            en="Min impurity decrease", es="Disminución mínima de impureza"
        ),
    )  # type: ignore

    random_state: schema_field(
        union_type(optimizer_int_field(ge=0), none_type(int)),
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


class DecisionTreeRegression(
    RegressionModel, SklearnLikeRegressor, _DecisionTreeRegressor
):
    """Decision tree regressor that recursively partitions the feature space.

    DecisionTreeRegressor builds a binary tree by choosing the split that most
    reduces the MSE (default) at each internal node. Leaf nodes predict the mean
    of the training targets in the region. Decision trees are fast, interpretable,
    and require no feature scaling, but tend to overfit without pruning.

    Key hyperparameters include ``max_depth``, ``min_samples_split``,
    ``min_samples_leaf``, and ``max_leaf_nodes``. The implementation wraps
    scikit-learn's ``DecisionTreeRegressor``.

    References
    ----------
    - [1] Breiman, L. et al. (1984). Classification and Regression Trees. Wadsworth.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeRegressor.html
    """

    SCHEMA = DecisionTreeRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Decision Tree Regression",
        es="Regresión Árbol de Decisión",
    )
    DESCRIPTION: str = MultilingualString(
        en="Interpretable tree-based regressor that partitions the feature space.",
        es=(
            "Regresor basado en árbol interpretable que particiona el espacio "
            "de características."
        ),
    )
    COLOR: str = "#66BB6A"
    ICON: str = "AccountTree"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
