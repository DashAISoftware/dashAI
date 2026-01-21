from sklearn.neighbors import KNeighborsClassifier as _KNeighborsClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
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


class KNeighborsClassifierSchema(BaseSchema):
    """KNN is a supervised classification method that determines the probability of
    an element belonging to a certain class by considering its k closest neighbors.
    """

    n_neighbors: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 5,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "The number of neighbors to consider "
                "in each input for classification. "
            ),
            es=(
                "Es el número de vecinos a considerar en "
                "cada entrada para la clasificación. "
            ),
        ),
        alias=MultilingualString(en="N neighbors", es="N vecinos"),
    )  # type: ignore
    weights: schema_field(
        enum_field(enum=["uniform", "distance"]),
        placeholder="uniform",
        description=MultilingualString(
            en="The parameter must be 'uniform' or 'distance'.",
            es="El parámetro debe ser 'uniform' o 'distance'.",
        ),
        alias=MultilingualString(en="Weights", es="Pesos"),
    )  # type: ignore
    algorithm: schema_field(
        enum_field(enum=["auto", "ball_tree", "kd_tree", "brute"]),
        placeholder="auto",
        description=MultilingualString(
            en=("The parameter must be 'auto', 'ball_tree', " "'kd_tree', or 'brute'."),
            es=("El parámetro debe ser 'auto', 'ball_tree', " "'kd_tree' o 'brute'.",),
        ),
        alias=MultilingualString(en="Algorithm", es="Algoritmo"),
    )  # type: ignore


class KNeighborsClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _KNeighborsClassifier
):
    """Scikit-learn's K-Nearest Neighbors (KNN) classifier wrapper for DashAI."""

    SCHEMA = KNeighborsClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="K-Nearest Neighbors (KNN)",
        es="K-Vecinos más Cercanos (KNN)",
    )
    DESCRIPTION: str = MultilingualString(
        en="Classification based on k nearest training examples in feature space.",
        es=(
            "Clasificación basada en los k ejemplos de entrenamiento más cercanos en "
            "el espacio de características."
        ),
    )
    COLOR: str = "#FFD54F"
    ICON: str = "ScatterPlot"

    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
