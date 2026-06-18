"""DashAI K-Means clustering model."""

from sklearn.cluster import KMeans as _KMeans

from DashAI.back.core.schema_fields import (
    enum_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_clusterer import (
    SklearnLikeClusterer,
)


class KMeansClusteringSchema(BaseSchema):
    """Schema that configures the K-Means clustering model.

    K-Means partitions the dataset into a fixed number of clusters by
    iteratively assigning samples to the nearest centroid and updating each
    centroid as the mean of its assigned samples. It is appropriate when the
    expected number of compact, centroid-shaped groups is known in advance.
    """

    n_clusters: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 8,
            "lower_bound": 2,
            "upper_bound": 12,
        },
        description=MultilingualString(
            en="Number of clusters to form.",
            es="Número de clusters a formar.",
        ),
        alias=MultilingualString(en="Clusters", es="Clusters"),
    )  # type: ignore
    init: schema_field(
        enum_field(["k-means++", "random"]),
        "k-means++",
        description=MultilingualString(
            en=(
                "Centroid initialisation method. 'k-means++' selects initial centroids "
                "to speed up convergence; 'random' picks them uniformly at random."
            ),
            es=(
                "Método de inicialización de centroides. "
                "'k-means++' selecciona centroides iniciales "
                "para acelerar la convergencia; 'random' los elige al azar."
            ),
        ),
        alias=MultilingualString(en="Init method", es="Método de inicio"),
    )  # type: ignore
    max_iter: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 300,
            "lower_bound": 10,
            "upper_bound": 1000,
        },
        description=MultilingualString(
            en="Maximum number of iterations for a single run.",
            es="Número máximo de iteraciones por ejecución.",
        ),
        alias=MultilingualString(en="Max iterations", es="Iteraciones máximas"),
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
            en="Random seed used by K-Means.",
            es="Semilla aleatoria usada por K-Means.",
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
    )  # type: ignore


class KMeansClustering(SklearnLikeClusterer, _KMeans):
    """K-Means clustering model for the Models module.

    K-Means is a centroid-based unsupervised algorithm. It fits ``n_clusters``
    centroids and assigns each sample to the closest centroid according to the
    Euclidean distance used by scikit-learn's implementation. The model exposes
    cluster labels for comparison metrics such as Silhouette,
    Davies-Bouldin, and Calinski-Harabasz.

    Key hyperparameters include ``n_clusters`` (the number of groups to form)
    and ``random_state`` (seed used for centroid initialisation). The
    implementation wraps scikit-learn's ``KMeans`` estimator.

    References
    ----------
    - [1] MacQueen, J. (1967). "Some methods for classification and analysis
           of multivariate observations."
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html
    """

    SCHEMA = KMeansClusteringSchema
    DISPLAY_NAME = MultilingualString(en="K-Means", es="K-Means")
    DESCRIPTION = MultilingualString(
        en="Partitions samples into a fixed number of clusters.",
        es="Agrupa muestras en un número fijo de clusters.",
    )
    COLOR = "#26A69A"
    ICON = "Hub"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper. See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)

    def get_fit_attributes(self) -> dict:
        """Return K-Means post-fit attributes for the converter report."""
        return {
            "cluster_centers": self.cluster_centers_.tolist(),
            "inertia": float(self.inertia_),
        }
