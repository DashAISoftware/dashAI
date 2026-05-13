from sklearn.ensemble import ExtraTreesRegressor as _ExtraTreesRegressor

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
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class ExtraTreesRegressionSchema(BaseSchema):
    """Schema that configures the Extra-Trees Regressor.

    Extra-Trees (Extremely Randomised Trees) builds an ensemble of decision tree
    regressors with fully random feature thresholds, further reducing variance
    compared to Random Forests. The underlying implementation is
    ``sklearn.ensemble.ExtraTreesRegressor``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 50,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en="The number of trees in the forest.",
            es="El número de árboles en el bosque.",
            pt="O número de árvores na floresta.",
        ),
        alias=MultilingualString(
            en="N estimators", es="N estimadores", pt="N estimadores"
        ),
    )  # type: ignore

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
            pt=(
                "A profundidade máxima da árvore. Se None, os nós são expandidos "
                "até que todas as folhas sejam puras ou restem menos de "
                "min_samples_split amostras."
            ),
        ),
        alias=MultilingualString(
            en="Max depth", es="Profundidad máxima", pt="Profundidade máxima"
        ),
    )  # type: ignore

    min_samples_split: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 2,
            "lower_bound": 2,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en="Minimum number of samples required to split an internal node.",
            es="Número mínimo de muestras requeridas para dividir un nodo interno.",
            pt="Número mínimo de amostras necessárias para dividir um nó interno.",
        ),
        alias=MultilingualString(
            en="Min samples split",
            es="Mínimas muestras de división",
            pt="Mínimas amostras de divisão",
        ),
    )  # type: ignore

    min_samples_leaf: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en="Minimum number of samples required to be at a leaf node.",
            es="Número mínimo de muestras requeridas para estar en una hoja.",
            pt="Número mínimo de amostras necessárias para estar em um nó folha.",
        ),
        alias=MultilingualString(
            en="Min samples leaf",
            es="Mínimas muestras para hoja",
            pt="Mínimas amostras para folha",
        ),
    )  # type: ignore

    bootstrap: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=(
                "Whether bootstrap samples are used when building trees. "
                "If False, the whole dataset is used for each tree."
            ),
            es=(
                "Si se usan muestras bootstrap al construir los árboles. "
                "Si es False, se usa todo el conjunto de datos para cada árbol."
            ),
            pt=(
                "Se amostras bootstrap são usadas ao construir as árvores. "
                "Se False, o conjunto de dados completo é usado para cada árvore."
            ),
        ),
        alias=MultilingualString(en="Bootstrap", es="Bootstrap", pt="Bootstrap"),
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
            pt=(
                "A semente do gerador de números pseudoaleatórios. Passe um int para "
                "saída reproduzível, ou None para não definir uma semente específica."
            ),
        ),
        alias=MultilingualString(
            en="Random state", es="Estado aleatorio", pt="Estado aleatório"
        ),
    )  # type: ignore


class ExtraTreesRegression(RegressionModel, SklearnLikeRegressor, _ExtraTreesRegressor):
    """Extra-Trees regressor using fully randomised decision tree splits.

    Extremely Randomised Trees pick thresholds at random instead of searching for
    the optimal split, introducing extra randomness that further reduces variance.
    Combined with averaging over many trees, Extra-Trees can achieve very low
    generalisation error on regression tasks while being fast to train.

    Key hyperparameters include ``n_estimators``, ``max_depth``,
    ``min_samples_split``, and ``bootstrap``. The implementation wraps
    scikit-learn's ``ExtraTreesRegressor``.

    References
    ----------
    - [1] Geurts, P., Ernst, D. & Wehenkel, L. (2006). "Extremely randomized trees."
           Machine Learning, 63(1), 3-42.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html
    """

    SCHEMA = ExtraTreesRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Extra-Trees Regression",
        es="Regresión Extra-Trees",
        pt="Regressor de Árvores Extras",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Ensemble of fully randomised decision trees for fast, "
            "low-variance regression."
        ),
        es=(
            "Conjunto de árboles de decisión completamente aleatorizados "
            "para regresión rápida y de baja varianza."
        ),
        pt=(
            "Conjunto de árvores de decisão completamente aleatorizadas "
            "para regressão rápida e de baixa variância."
        ),
    )
    COLOR: str = "#26A69A"
    ICON: str = "Park"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
