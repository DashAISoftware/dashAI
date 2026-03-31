from sklearn.ensemble import RandomForestClassifier as _RandomForestClassifier

from DashAI.back.core.schema_fields import BaseSchema, optimizer_int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class RandomForestClassifierSchema(BaseSchema):
    """Schema that configures the Random Forest Classifier.

    Random Forest is an ensemble classification algorithm that builds multiple
    decision trees on bootstrap samples of the training data, using a random subset
    of features at each split, and aggregates their predictions by majority vote.
    The underlying implementation is ``sklearn.ensemble.RandomForestClassifier``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 50,
            "upper_bound": 200,
        },
        description=MultilingualString(
            en=(
                "The 'n_estimators' parameter corresponds to the number of decision "
                "trees. It must be an integer greater than or equal to 1."
            ),
            es=(
                "El parámetro 'n_estimators' corresponde al número de árboles de "
                "decisión. Debe ser un entero mayor o igual a 1."
            ),
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore
    max_depth: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 2,
            "lower_bound": 2,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "The parameter corresponds to the maximum depth of the "
                "tree. It must be an integer greater than or equal to 1."
            ),
            es=(
                "El parámetro corresponde a la profundidad máxima del "
                "árbol. Debe ser un entero mayor o igual a 1."
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
            en=(
                "This parameter sets the minimum number of samples "
                "required to split an internal node. It must be a number greater than "
                "or equal to 2."
            ),
            es=(
                "Este parámetro establece el número mínimo de muestras "
                "requeridas para dividir un nodo interno. Debe ser un número mayor o "
                "igual a 2."
            ),
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
            en=(
                "This parameter sets the minimum number of samples "
                "required to be at a leaf node. It must be a number greater than or "
                "equal to 1."
            ),
            es=(
                "Este parámetro establece el número mínimo de muestras "
                "requeridas para estar en una hoja. Debe ser un número mayor o igual "
                "a 1."
            ),
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
        ),
    )  # type: ignore
    max_leaf_nodes: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 2,
            "lower_bound": 2,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=(
                "This parameter sets the maximum number of leaf nodes. It must be an "
                "integer greater than or equal to 2."
            ),
            es=(
                "Este parámetro establece el número máximo de nodos hoja. Debe ser un "
                "entero mayor o igual a 2."
            ),
        ),
        alias=MultilingualString(en="Max leaf nodes", es="Máximos nodos para hoja"),
    )  # type: ignore
    random_state: schema_field(
        optimizer_int_field(ge=0),
        placeholder={
            "optimize": False,
            "fixed_value": 0,
            "lower_bound": 0,
            "upper_bound": 10,
        },
        description=MultilingualString(
            en=("This parameter must be an integer greater than or equal to 0."),
            es=("Este parámetro debe ser un entero mayor o igual a 0."),
        ),
        alias=MultilingualString(en="Random State", es="Estado Aleatorio"),
    )  # type: ignore


class RandomForestClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _RandomForestClassifier
):
    """Random forest classifier that aggregates predictions from many decision trees.

    Random Forest is a bagging ensemble that fits ``n_estimators`` decision trees,
    each on a bootstrap sample of the training data. At each split only a random
    subset of features is evaluated, which decorrelates the trees and reduces
    variance. The final class prediction is determined by majority vote across all
    trees.

    Key hyperparameters include ``n_estimators`` (number of trees), ``max_depth``
    (maximum tree depth), ``min_samples_split``, ``min_samples_leaf``,
    ``max_leaf_nodes``, and ``random_state``. The implementation wraps
    scikit-learn's ``RandomForestClassifier``.

    References
    ----------
    .. [1] Breiman, L. (2001). "Random Forests." Machine Learning, 45(1), 5-32.
           https://doi.org/10.1023/A:1010933404324
    .. [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html
    """

    SCHEMA = RandomForestClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Random Forest",
        es="Bosque Aleatorio",
    )
    DESCRIPTION: str = MultilingualString(
        en="An ensemble learning method using multiple decision trees.",
        es=(
            "Un método de aprendizaje en conjunto que utiliza múltiples árboles de "
            "decisión."
        ),
    )
    COLOR: str = "#FF8A65"
    ICON: str = "Forest"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.  See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
