"""DashAI Gaussian Mixture Model (GMM) clustering model."""

from sklearn.mixture import GaussianMixture as _GaussianMixture

from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_clusterer import (
    SklearnLikeClusterer,
)


class GaussianMixtureClusteringSchema(BaseSchema):
    """Schema that configures the Gaussian Mixture Model clustering model.

    GMM models the data as a weighted sum of Gaussian distributions. Each
    sample is assigned a soft membership probability for every component and is
    labelled with the highest-probability component. Unlike centroid-based
    algorithms, GMM supports elliptical cluster shapes and exposes BIC/AIC for
    model selection.
    """

    n_components: schema_field(
        int_field(ge=1),
        placeholder=2,
        description=MultilingualString(
            en="Number of Gaussian components (clusters) to fit.",
            es="Número de componentes gaussianas (clusters) a ajustar.",
        ),
        alias=MultilingualString(en="Components", es="Componentes"),
    )  # type: ignore
    covariance_type: schema_field(
        enum_field(["full", "tied", "diag", "spherical"]),
        "full",
        description=MultilingualString(
            en=(
                "Shape of covariance matrices. 'full' is most flexible; "
                "'spherical' is most constrained."
            ),
            es=(
                "Forma de las matrices de covarianza. 'full' es la más flexible; "
                "'spherical' es la más restringida."
            ),
        ),
        alias=MultilingualString(en="Covariance type", es="Tipo de covarianza"),
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=1),
        placeholder=100,
        description=MultilingualString(
            en="Maximum number of EM algorithm iterations.",
            es="Número máximo de iteraciones del algoritmo EM.",
        ),
        alias=MultilingualString(en="Max iterations", es="Iteraciones máximas"),
    )  # type: ignore
    random_state: schema_field(
        int_field(ge=0),
        placeholder=0,
        description=MultilingualString(
            en="Random seed used for initialisation.",
            es="Semilla aleatoria usada para la inicialización.",
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore


class GaussianMixtureClustering(SklearnLikeClusterer, _GaussianMixture):
    """Gaussian Mixture Model clustering model for the Models module.

    GMM is a probabilistic unsupervised algorithm. It fits a mixture of
    Gaussian distributions to the data using the Expectation-Maximisation
    algorithm. Each sample is assigned to the component with the highest
    posterior probability, producing soft cluster memberships that enable
    richer analyses than hard assignments.

    Key hyperparameters include ``n_components`` (number of clusters),
    ``covariance_type`` (shape of covariance matrices), ``max_iter``
    (EM convergence budget), and ``random_state`` (seed). The implementation
    wraps scikit-learn's ``GaussianMixture`` estimator.

    References
    ----------
    - [1] Dempster, A. P., Laird, N. M., & Rubin, D. B. (1977). "Maximum
           likelihood from incomplete data via the EM algorithm."
    - [2] https://scikit-learn.org/stable/modules/generated/
           sklearn.mixture.GaussianMixture.html
    """

    SCHEMA = GaussianMixtureClusteringSchema
    DISPLAY_NAME = MultilingualString(en="Gaussian Mixture", es="Mezcla Gaussiana")
    DESCRIPTION = MultilingualString(
        en="Probabilistic clustering using mixtures of Gaussian distributions.",
        es="Clustering probabilístico usando mezclas de distribuciones gaussianas.",
    )
    COLOR = "#FF7043"
    ICON = "BubbleChart"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper. See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
