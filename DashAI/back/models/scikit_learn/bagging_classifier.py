from sklearn.ensemble import BaggingClassifier as _BaggingClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class BaggingClassifierSchema(BaseSchema):
    """Schema that configures the Bagging Classifier.

    Bagging (Bootstrap Aggregating) fits base classifiers on random subsets of the
    training data (drawn with replacement) and aggregates their predictions by
    majority vote. It reduces variance and helps avoid overfitting. The underlying
    implementation is ``sklearn.ensemble.BaggingClassifier``.
    """

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 10,
            "lower_bound": 5,
            "upper_bound": 100,
        },
        description=MultilingualString(
            en="The number of base estimators in the ensemble.",
            es="El número de estimadores base en el conjunto.",
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore

    max_samples: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.1,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Fraction of training samples drawn for each base estimator "
                "(0 < max_samples ≤ 1.0)."
            ),
            es=(
                "Fracción de muestras de entrenamiento para cada estimador base "
                "(0 < max_samples ≤ 1.0)."
            ),
        ),
        alias=MultilingualString(en="Max samples", es="Máximas muestras"),
    )  # type: ignore

    max_features: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.1,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "Fraction of features drawn for each base estimator "
                "(0 < max_features ≤ 1.0)."
            ),
            es=(
                "Fracción de características para cada estimador base "
                "(0 < max_features ≤ 1.0)."
            ),
        ),
        alias=MultilingualString(en="Max features", es="Máximas características"),
    )  # type: ignore

    bootstrap: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether to draw samples with replacement.",
            es="Si se extraen muestras con reemplazo.",
        ),
        alias=MultilingualString(en="Bootstrap", es="Bootstrap"),
    )  # type: ignore

    bootstrap_features: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en="Whether to draw features with replacement.",
            es="Si se extraen características con reemplazo.",
        ),
        alias=MultilingualString(
            en="Bootstrap features", es="Bootstrap características"
        ),
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


class BaggingClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _BaggingClassifier
):
    """Bagging classifier that aggregates predictions from bootstrap subsets.

    Bagging builds multiple base classifiers, each trained on a bootstrap sample of
    the training data. The final class prediction is determined by majority voting.
    Bagging is particularly effective with high-variance, low-bias estimators such
    as decision trees.

    Key hyperparameters include ``n_estimators``, ``max_samples``,
    ``max_features``, and ``bootstrap``. The implementation wraps scikit-learn's
    ``BaggingClassifier``.

    References
    ----------
    - [1] Breiman, L. (1996). "Bagging Predictors." Machine Learning, 24(2), 123-140.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.BaggingClassifier.html
    """

    SCHEMA = BaggingClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Bagging Classifier",
        es="Clasificador Bagging",
    )
    DESCRIPTION: str = MultilingualString(
        en="Bootstrap aggregating ensemble to reduce variance.",
        es="Conjunto de bootstrap aggregating para reducir la varianza.",
    )
    COLOR: str = "#26C6DA"
    ICON: str = "Inventory"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
