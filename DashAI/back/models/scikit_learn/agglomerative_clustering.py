"""DashAI Agglomerative (Hierarchical) clustering model."""

from sklearn.cluster import AgglomerativeClustering as _AgglomerativeClustering

from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_clusterer import (
    SklearnLikeClusterer,
)


class AgglomerativeClusteringSchema(BaseSchema):
    """Schema that configures the Agglomerative clustering model.

    Agglomerative clustering builds a hierarchy by iteratively merging the
    pair of clusters that minimises the chosen linkage criterion. It does not
    require specifying the number of clusters in advance when a dendrogram is
    analysed, but exposing ``n_clusters`` lets the user cut the hierarchy at a
    desired level.
    """

    n_clusters: schema_field(
        int_field(ge=2),
        placeholder=2,
        description=MultilingualString(
            en="Number of clusters to find.",
            es="Número de clusters a encontrar.",
        ),
        alias=MultilingualString(en="Clusters", es="Clusters"),
    )  # type: ignore
    linkage: schema_field(
        enum_field(["ward", "complete", "average", "single"]),
        "ward",
        description=MultilingualString(
            en=(
                "Linkage criterion determining which distances to use between "
                "clusters. 'ward' minimises variance and only supports "
                "'euclidean' metric."
            ),
            es=(
                "Criterio de enlace que determina la distancia entre clusters. "
                "'ward' minimiza la varianza y solo admite la métrica 'euclidean'."
            ),
        ),
        alias=MultilingualString(en="Linkage", es="Enlace"),
    )  # type: ignore
    metric: schema_field(
        enum_field(["euclidean", "manhattan", "cosine"]),
        "euclidean",
        description=MultilingualString(
            en=(
                "Distance metric used to compute linkage. "
                "'ward' linkage only supports 'euclidean'."
            ),
            es=(
                "Métrica de distancia usada para el enlace. "
                "El enlace 'ward' solo admite 'euclidean'."
            ),
        ),
        alias=MultilingualString(en="Metric", es="Métrica"),
    )  # type: ignore
    compute_distances: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "Whether to compute and store merge distances during fitting. "
                "Required to render a dendrogram. Has a small memory cost "
                "proportional to the number of samples."
            ),
            es=(
                "Si se calculan y almacenan las distancias de fusión durante el "
                "ajuste. Necesario para renderizar el dendrograma. Tiene un "
                "pequeño costo de memoria proporcional al número de muestras."
            ),
        ),
        alias=MultilingualString(en="Compute distances", es="Calcular distancias"),
    )  # type: ignore


class AgglomerativeClustering(SklearnLikeClusterer, _AgglomerativeClustering):
    """Agglomerative hierarchical clustering model for the Models module.

    Agglomerative clustering is a bottom-up hierarchical algorithm. Each sample
    starts as its own cluster; clusters are merged successively according to the
    chosen ``linkage`` criterion until ``n_clusters`` groups remain. The
    algorithm exposes cluster labels for comparison metrics such as Silhouette,
    Davies-Bouldin, and Calinski-Harabasz.

    Key hyperparameters include ``n_clusters`` (cut level of the hierarchy),
    ``linkage`` (merge strategy), and ``metric`` (distance function). The
    implementation wraps scikit-learn's ``AgglomerativeClustering`` estimator.

    References
    ----------
    - [1] Ward, J. H. (1963). "Hierarchical grouping to optimize an objective
           function."
    - [2] https://scikit-learn.org/stable/modules/generated/
           sklearn.cluster.AgglomerativeClustering.html
    """

    SCHEMA = AgglomerativeClusteringSchema
    DISPLAY_NAME = MultilingualString(en="Agglomerative", es="Aglomerativo")
    DESCRIPTION = MultilingualString(
        en="Hierarchical clustering by progressively merging groups.",
        es="Clustering jerárquico que fusiona grupos progresivamente.",
    )
    COLOR = "#42A5F5"
    ICON = "AccountTree"

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
        """Return Agglomerative post-fit attributes for the converter report."""
        distances = (
            self.distances_.tolist()
            if hasattr(self, "distances_")
            else list(range(len(self.children_)))
        )
        return {
            "linkage_data": {
                "children": self.children_.tolist(),
                "distances": distances,
                "n_leaves": len(self._labels),
            }
        }
