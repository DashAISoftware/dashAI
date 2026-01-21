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
    """Decision Trees are a set of are a non-parametric supervised learning method that
    learns simple decision rules (structured as a tree) inferred from the data features.
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
        alias=MultilingualString(en="criterion", es="criterio"),
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
        alias=MultilingualString(en="max_depth", es="profundidad_maxima"),
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
        alias=MultilingualString(en="min_samples_split", es="min_muestras_division"),
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
        alias=MultilingualString(en="min_samples_leaf", es="min_muestras_hoja"),
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
        alias=MultilingualString(en="max_features", es="max_caracteristicas"),
    )  # type: ignore


class DecisionTreeClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _DecisionTreeClassifier
):
    """Scikit-learn's Decision Tree Classifier wrapper for DashAI."""

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
        super().__init__(**kwargs)
