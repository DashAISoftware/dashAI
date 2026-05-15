from sklearn.ensemble import ExtraTreesClassifier as _ExtraTreesClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    none_type,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class ExtraTreesClassifierSchema(BaseSchema):
    """Schema that configures the Extra-Trees Classifier.

    Extra-Trees (Extremely Randomised Trees) builds an ensemble of decision trees
    with fully random feature thresholds, which further reduces variance at the
    cost of a slightly higher bias compared to Random Forests. The underlying
    implementation is ``sklearn.ensemble.ExtraTreesClassifier``.
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
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore

    max_depth: schema_field(
        none_type(optimizer_int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The maximum depth of the tree. If None, nodes are expanded until "
                "all leaves are pure or contain fewer than min_samples_split samples."
            ),
            es=(
                "La profundidad máxima del árbol. Si es None, los nodos se expanden "
                "hasta que todas las hojas sean puras o tengan menos de "
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
            "upper_bound": 10,
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
            "upper_bound": 10,
        },
        description=MultilingualString(
            en="The minimum number of samples required to be at a leaf node.",
            es="El número mínimo de muestras requeridas para estar en una hoja.",
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
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
        ),
        alias=MultilingualString(en="Bootstrap", es="Bootstrap"),
    )  # type: ignore

    random_state: schema_field(
        none_type(optimizer_int_field(ge=0)),
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


class ExtraTreesClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _ExtraTreesClassifier
):
    """Extra-Trees classifier using fully randomised decision tree splits.

    Extremely Randomised Trees differ from Random Forests in how splits are chosen:
    instead of searching for the best threshold per feature, Extra-Trees picks
    thresholds at random. This introduces additional randomness that, combined with
    bootstrap aggregation, further reduces variance. Extra-Trees are typically faster
    to train than Random Forests.

    Key hyperparameters include ``n_estimators``, ``max_depth``,
    ``min_samples_split``, ``min_samples_leaf``, and ``bootstrap``. The
    implementation wraps scikit-learn's ``ExtraTreesClassifier``.

    References
    ----------
    - [1] Geurts, P., Ernst, D. & Wehenkel, L. (2006). "Extremely randomized trees."
           Machine Learning, 63(1), 3-42. https://doi.org/10.1007/s10994-006-6226-1
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html
    """

    SCHEMA = ExtraTreesClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Extra-Trees Classifier",
        es="Clasificador Extra-Trees",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Ensemble of fully randomised decision trees for fast, "
            "low-variance classification."
        ),
        es=(
            "Conjunto de árboles de decisión completamente aleatorizados "
            "para clasificación rápida."
        ),
    )
    COLOR: str = "#66BB6A"
    ICON: str = "Park"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
