"""DashAI HDBSCAN clustering model."""

from sklearn.cluster import HDBSCAN as _HDBSCAN

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


class HDBSCANClusteringSchema(BaseSchema):
    """Schema that configures the HDBSCAN clustering model.

    HDBSCAN extends DBSCAN by running it at multiple density thresholds and
    extracting the most stable clusters via a condensed cluster tree. It handles
    clusters of varying density, eliminates the manual ``eps`` parameter, and
    assigns soft cluster membership scores (``probabilities_``).
    """

    min_cluster_size: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 2,
            "upper_bound": 50,
        },
        description=MultilingualString(
            en="Minimum number of samples required to form a cluster.",
            es="Mínimo de muestras requeridas para formar un cluster.",
        ),
        alias=MultilingualString(en="Min cluster size", es="Tamaño mínimo de cluster"),
    )  # type: ignore
    min_samples: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 5,
            "lower_bound": 1,
            "upper_bound": 20,
        },
        description=MultilingualString(
            en=(
                "Number of samples in a neighbourhood for a point "
                "to be considered a core point."
            ),
            es=(
                "Número de muestras en una vecindad para que un punto "
                "sea considerado central."
            ),
        ),
        alias=MultilingualString(en="Min samples", es="Mínimo de muestras"),
    )  # type: ignore
    metric: schema_field(
        enum_field(["euclidean", "manhattan", "cosine"]),
        "euclidean",
        description=MultilingualString(
            en="Distance metric used to compute core distances.",
            es="Métrica de distancia usada para calcular distancias centrales.",
        ),
        alias=MultilingualString(en="Metric", es="Métrica"),
    )  # type: ignore


class HDBSCANClustering(SklearnLikeClusterer, _HDBSCAN):
    """HDBSCAN clustering model for the Models module.

    HDBSCAN is a hierarchical density-based unsupervised algorithm. It builds a
    minimum spanning tree over core distances, converts it to a cluster
    hierarchy, and selects the most persistent clusters. Noise samples are
    labelled ``-1``. Unlike DBSCAN, it supports clusters of varying density
    without requiring a global ``eps`` parameter.

    Key hyperparameters include ``min_cluster_size`` (smallest group accepted),
    ``min_samples`` (core-point threshold), and ``metric`` (distance function).
    Requires scikit-learn >= 1.3. The implementation wraps scikit-learn's
    ``HDBSCAN`` estimator.

    References
    ----------
    - [1] Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013).
           "Density-Based Clustering Based on Hierarchical Density Estimates."
    - [2] https://scikit-learn.org/stable/modules/generated/
           sklearn.cluster.HDBSCAN.html
    """

    SCHEMA = HDBSCANClusteringSchema
    DISPLAY_NAME = MultilingualString(en="HDBSCAN", es="HDBSCAN")
    DESCRIPTION = MultilingualString(
        en="Hierarchical density-based clustering with variable density support.",
        es="Clustering jerárquico basado en densidad con soporte de densidad variable.",
    )
    COLOR = "#26C6DA"
    ICON = "Layers"

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
        """Return HDBSCAN post-fit attributes for the converter report."""
        import numpy as np

        attrs = {"cluster_persistence": self.cluster_persistence_.tolist()}
        n_noise = int(np.sum(self._labels == -1))
        if n_noise > 0:
            attrs["n_noise_points"] = n_noise
        return attrs
