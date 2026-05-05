from sklearn.ensemble import AdaBoostClassifier as _AdaBoostClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class AdaBoostClassifierSchema(BaseSchema):
    """Schema that configures the AdaBoost Classifier.

    AdaBoost (Adaptive Boosting) fits a sequence of weak learners on repeatedly
    re-weighted versions of the training data. Misclassified samples receive
    increased weight so that subsequent learners focus on harder examples. The
    underlying implementation is ``sklearn.ensemble.AdaBoostClassifier``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 50,
            "lower_bound": 10,
            "upper_bound": 500,
        },
        description=MultilingualString(
            en=(
                "The maximum number of estimators at which boosting is terminated. "
                "In case of perfect fit, the learning procedure is stopped early."
            ),
            es=(
                "El número máximo de estimadores en el que se termina el boosting. "
                "En caso de ajuste perfecto, el procedimiento de aprendizaje se "
                "detiene antes."
            ),
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore

    learning_rate: schema_field(
        optimizer_float_field(ge=0.01),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.01,
            "upper_bound": 2.0,
        },
        description=MultilingualString(
            en=(
                "Weight applied to each classifier at each boosting iteration. "
                "A higher learning rate increases the contribution of each classifier."
            ),
            es=(
                "Peso aplicado a cada clasificador en cada iteración de boosting. "
                "Una tasa de aprendizaje mayor incrementa la contribución de cada "
                "clasificador."
            ),
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
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


class AdaBoostClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _AdaBoostClassifier
):
    """AdaBoost classifier that adapts to misclassified samples iteratively.

    AdaBoost fits a sequence of weak classifiers (decision stumps by default) on
    re-weighted training data, giving more weight to misclassified examples at each
    round. The final prediction is a weighted majority vote of all weak classifiers.
    AdaBoost is sensitive to noisy data and outliers.

    Key hyperparameters include ``n_estimators``, ``learning_rate``, and
    ``random_state``. The implementation wraps scikit-learn's
    ``AdaBoostClassifier``.

    References
    ----------
    - [1] Freund, Y. & Schapire, R.E. (1997). "A Decision-Theoretic Generalization
           of On-Line Learning and an Application to Boosting." Journal of Computer
           and System Sciences, 55(1), 119-139.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.AdaBoostClassifier.html
    """

    SCHEMA = AdaBoostClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="AdaBoost Classifier",
        es="Clasificador AdaBoost",
    )
    DESCRIPTION: str = MultilingualString(
        en="Adaptive boosting that focuses on misclassified samples.",
        es="Boosting adaptivo que se enfoca en muestras mal clasificadas.",
    )
    COLOR: str = "#FFA726"
    ICON: str = "Bolt"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
