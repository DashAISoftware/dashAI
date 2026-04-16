from sklearn.tree import DecisionTreeClassifier as _DecisionTreeClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    none_type,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class DecisionTreeClassifierSchema(BaseSchema):
    """Schema that configures the Decision Tree Classifier.

    Decision Trees are a non-parametric supervised classification method that
    recursively partitions the feature space by learning axis-aligned decision rules
    inferred from training data. The tree structure is built using the CART algorithm.
    The underlying implementation is ``sklearn.tree.DecisionTreeClassifier``.
    """

    criterion: schema_field(
        enum_field(enum=["entropy", "gini", "log_loss"]),
        placeholder="entropy",
        description=MultilingualString(
            en=(
                "The function to measure the quality of a split. Supported criteria "
                "are “gini” for the Gini impurity and “log_loss” and “entropy” both "
                "for the Shannon information gain."
            ),
            es=(
                "La función para medir la calidad de una división. Los criterios "
                "soportados son “gini” para la impureza de Gini y “log_loss” y "
                "“entropy” para la ganancia de información de Shannon."
            ),
        ),
        alias=MultilingualString(en="Criterion", es="Criterio"),
    )  # type: ignore
    max_depth: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "The maximum depth of the tree. If None, then nodes are expanded "
                "until all leaves are pure or until all leaves contain less than "
                "min_samples_split samples."
            ),
            es=(
                "La profundidad máxima del árbol. Si es None, los nodos se expanden "
                "hasta que todas las hojas sean puras o hasta que todas las hojas "
                "contengan menos de min_samples_split muestras."
            ),
        ),
        alias=MultilingualString(en="Max depth", es="Profundidad máxima"),
    )  # type: ignore
    min_samples_split: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 5,
        },
        description=MultilingualString(
            en="The minimum number of samples required to split an internal node.",
            es="El número mínimo de muestras requeridas para dividir un nodo interno.",
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
            "upper_bound": 5,
        },
        description=MultilingualString(
            en="The minimum number of samples required to be at a leaf node.",
            es="El número mínimo de muestras requeridas para estar en una hoja.",
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
        ),
    )  # type: ignore
    max_features: schema_field(
        none_type(
            union_type(enum_field(enum=["sqrt", "log2"]), float_field(gt=0.0, le=1.0))
        ),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The number of features to consider when looking for the best split. "
                "If float, then max_features is a percentage of the total number of "
                "features."
            ),
            es=(
                "El número de características a considerar al buscar la mejor "
                "división. Si es float, entonces max_features es un porcentaje del "
                "total de características."
            ),
        ),
        alias=MultilingualString(en="Max features", es="Máximas características"),
    )  # type: ignore


class DecisionTreeClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _DecisionTreeClassifier
):
    """Decision tree classifier that learns axis-aligned decision rules from data.

    A decision tree recursively partitions the feature space into rectangular regions
    by choosing splits that maximise a purity criterion (Gini impurity, entropy, or
    log-loss). At prediction time the tree routes each sample to a leaf node whose
    majority class is returned as the prediction.

    The tree complexity is primarily controlled by ``max_depth``, ``min_samples_split``,
    ``min_samples_leaf``, and ``max_features``. Shallow trees are more interpretable
    but may underfit; very deep trees tend to overfit. The implementation wraps
    scikit-learn's ``DecisionTreeClassifier``, which uses the CART algorithm.

    References
    ----------
    - [1] Breiman, L., Friedman, J., Olshen, R., & Stone, C. (1984).
           "Classification and Regression Trees." Wadsworth.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html
    """

    SCHEMA = DecisionTreeClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Decision Tree",
        es="Árbol de Decisión",
    )
    DESCRIPTION: str = MultilingualString(
        en="Decision tree classifier using CART algorithm.",
        es=("Clasificador de árbol de decisión usando el algoritmo CART."),
    )
    COLOR: str = "#4CAF50"
    ICON: str = "AccountTree"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.  See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
