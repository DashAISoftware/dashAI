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
            de="Anzahl der Nachbarn für die Vorhersage.",
        ),
        alias=MultilingualString(
            en="N neighbors", es="N vecinos", pt="N vizinhos", de="Anzahl Nachbarn"
        ),
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
            de=(
                "Gewichtungsfunktion für die Vorhersage. 'uniform' gewichtet alle "
                "Nachbarn gleich; 'distance' gewichtet nach inverser Distanz."
            ),
        ),
        alias=MultilingualString(en="Weights", es="Pesos", pt="Pesos", de="Gewichte"),
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
            de=(
                "Algorithmus zur Berechnung der nächsten Nachbarn. 'auto' wählt den "
                "besten basierend auf den an fit übergebenen Werten."
            ),
        ),
        alias=MultilingualString(
            en="Algorithm", es="Algoritmo", pt="Algoritmo", de="Algorithmus"
        ),
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
            de=(
                "Blattgröße für BallTree oder KDTree. Beeinflusst die "
                "Abfragegeschwindigkeit "
                "und den Speicherbedarf für den Baum."
            ),
        ),
        alias=MultilingualString(
            en="Leaf size", es="Tamaño de hoja", pt="Tamanho de folha", de="Blattgröße"
        ),
    )  # type: ignore

    metric: schema_field(
        enum_field(enum=["minkowski", "euclidean", "manhattan", "chebyshev"]),
        placeholder="minkowski",
        description=MultilingualString(
            en="Distance metric to use for the neighbour search.",
            es="Métrica de distancia para la búsqueda de vecinos.",
            pt="Métrica de distância para a busca de vizinhos.",
            de="Distanzmetrik für die Nachbarsuche.",
        ),
        alias=MultilingualString(en="Metric", es="Métrica", pt="Métrica", de="Metrik"),
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
        de="K-Nächste-Nachbarn-Regression",
        zh="K 近邻回归",
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
        de=(
            "Nicht-parametrische Regression, die durch Mittelung der nächsten "
            "Nachbarn vorhersagt."
        ),
        zh="通过对最近邻样本取平均进行预测的非参数回归方法。",
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
