from sklearn.naive_bayes import GaussianNB as _GaussianNB

from DashAI.back.core.schema_fields import (
    BaseSchema,
    optimizer_float_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class GaussianNBSchema(BaseSchema):
    """Schema that configures the Gaussian Naïve Bayes Classifier.

    Gaussian Naïve Bayes assumes that the continuous features in each class follow
    a Gaussian (normal) distribution and applies Bayes' theorem with the strong
    independence assumption between features. The underlying implementation is
    ``sklearn.naive_bayes.GaussianNB``.
    """

    var_smoothing: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1e-9,
            "lower_bound": 1e-12,
            "upper_bound": 1e-3,
        },
        description=MultilingualString(
            en=(
                "Portion of the largest variance of all features that is added to "
                "variances for calculation stability."
            ),
            es=(
                "Porción de la mayor varianza de todas las características que se "
                "añade a las varianzas para estabilidad del cálculo."
            ),
        ),
        alias=MultilingualString(en="Var smoothing", es="Suavizado de varianza"),
    )  # type: ignore


class GaussianNB(TabularClassificationModel, SklearnLikeClassifier, _GaussianNB):
    """Gaussian Naïve Bayes classifier based on Bayes' theorem.

    GaussianNB models the likelihood of features as Gaussian distributions per
    class. It estimates the mean and variance of each feature in each class from
    the training data, then uses Bayes' theorem to compute the posterior class
    probability. Despite the strong independence assumption, it often performs well
    and is very fast.

    Key hyperparameter: ``var_smoothing`` (additive variance for numerical
    stability). The implementation wraps scikit-learn's ``GaussianNB``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.GaussianNB.html
    """

    SCHEMA = GaussianNBSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Gaussian Naïve Bayes",
        es="Naïve Bayes Gaussiano",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Probabilistic classifier based on Bayes' theorem "
            "with Gaussian likelihoods."
        ),
        es=(
            "Clasificador probabilístico basado en el teorema de Bayes "
            "con verosimilitudes gaussianas."
        ),
    )
    COLOR: str = "#AB47BC"
    ICON: str = "Functions"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
