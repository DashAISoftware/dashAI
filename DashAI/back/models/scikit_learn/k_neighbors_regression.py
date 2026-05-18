from sklearn.neighbors import KNeighborsRegressor as _KNeighborsRegressor

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_model import (
    CategoricalEncodingStrategy,
)
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class KNeighborsRegressionSchema(BaseSchema):
    """Schema that configures the K-Nearest Neighbours Regressor.

    KNeighborsRegressor predicts the target by averaging the targets of the
    ``n_neighbors`` nearest training samples. The underlying implementation is
    ``sklearn.neighbors.KNeighborsRegressor``.
    """

    n_neighbors: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 1,
            "upper_bound": 50,
        },
        description=MultilingualString(
            en="Number of neighbours to use for the prediction.",
            es="Número de vecinos a usar para la predicción.",
            pt="Número de vizinhos a usar para a previsão.",
        ),
        alias=MultilingualString(en="N neighbors", es="N vecinos", pt="N vizinhos"),
    )  # type: ignore

    weights: schema_field(
        enum_field(enum=["uniform", "distance"]),
        placeholder="uniform",
        description=MultilingualString(
            en=(
                "Weight function used in prediction. 'uniform' weights all "
                "neighbours equally; 'distance' weights by inverse distance."
            ),
            es=(
                "Función de pesos usada en la predicción. 'uniform' pondera igual "
                "todos los vecinos; 'distance' pondera por distancia inversa."
            ),
            pt=(
                "Função de pesos usada na previsão. 'uniform' pondera igualmente "
                "todos os vizinhos; 'distance' pondera pela distância inversa."
            ),
        ),
        alias=MultilingualString(en="Weights", es="Pesos", pt="Pesos"),
    )  # type: ignore

    algorithm: schema_field(
        enum_field(enum=["auto", "ball_tree", "kd_tree", "brute"]),
        placeholder="auto",
        description=MultilingualString(
            en=(
                "Algorithm used to compute nearest neighbours. 'auto' selects the "
                "best based on the values passed to fit."
            ),
            es=(
                "Algoritmo para computar los vecinos más cercanos. 'auto' selecciona "
                "el mejor en función de los valores pasados a fit."
            ),
            pt=(
                "Algoritmo para calcular os vizinhos mais próximos. 'auto' seleciona "
                "o melhor com base nos valores passados ao fit."
            ),
        ),
        alias=MultilingualString(en="Algorithm", es="Algoritmo", pt="Algoritmo"),
    )  # type: ignore

    leaf_size: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 30,
            "lower_bound": 5,
            "upper_bound": 100,
        },
        description=MultilingualString(
            en=(
                "Leaf size passed to BallTree or KDTree. Affects query speed "
                "and memory required to store the tree."
            ),
            es=(
                "Tamaño de hoja pasado a BallTree o KDTree. Afecta la velocidad "
                "de consulta y la memoria requerida para almacenar el árbol."
            ),
            pt=(
                "Tamanho de folha passado ao BallTree ou KDTree. Afeta a velocidade "
                "de consulta e a memória necessária para armazenar a árvore."
            ),
        ),
        alias=MultilingualString(
            en="Leaf size", es="Tamaño de hoja", pt="Tamanho de folha"
        ),
    )  # type: ignore

    metric: schema_field(
        enum_field(enum=["minkowski", "euclidean", "manhattan", "chebyshev"]),
        placeholder="minkowski",
        description=MultilingualString(
            en="Distance metric to use for the neighbour search.",
            es="Métrica de distancia para la búsqueda de vecinos.",
            pt="Métrica de distância para a busca de vizinhos.",
        ),
        alias=MultilingualString(en="Metric", es="Métrica", pt="Métrica"),
    )  # type: ignore


class KNeighborsRegression(RegressionModel, SklearnLikeRegressor, _KNeighborsRegressor):
    """K-Nearest Neighbours regressor that averages the targets of nearest samples.

    KNeighborsRegressor predicts the target value by computing the (weighted)
    mean of the ``n_neighbors`` closest training points. It is a non-parametric
    method: no training phase is needed, and predictions can capture non-linear
    patterns. Performance degrades in high-dimensional spaces.

    Key hyperparameters include ``n_neighbors``, ``weights``, ``algorithm``, and
    ``metric``. The implementation wraps scikit-learn's ``KNeighborsRegressor``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsRegressor.html
    """

    SCHEMA = KNeighborsRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="K-Nearest Neighbours Regression",
        es="Regresión K-Vecinos Más Cercanos",
        pt="Regressor K-Vizinhos",
    )
    DESCRIPTION: str = MultilingualString(
        en="Non-parametric regression that predicts by averaging nearest neighbours.",
        es=(
            "Regresión no paramétrica que predice promediando los vecinos más cercanos."
        ),
        pt=(
            "Regressão não paramétrica que prevê calculando a média dos vizinhos "
            "mais próximos."
        ),
    )
    COLOR: str = "#FFA726"
    ICON: str = "ScatterPlot"
    CATEGORICAL_ENCODING = CategoricalEncodingStrategy.ONE_HOT

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
