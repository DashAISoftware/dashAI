"""DashAI DBSCAN clustering model."""

from sklearn.cluster import DBSCAN as _DBSCAN

from DashAI.back.core.schema_fields import (
    enum_field,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_clusterer import (
    SklearnLikeClusterer,
)


class DBSCANClusteringSchema(BaseSchema):
    """Schema that configures the DBSCAN clustering model.

    DBSCAN groups samples by density. A point becomes a core point when at
    least ``min_samples`` points fall within distance ``eps`` under the selected
    metric. Dense regions become clusters and sparse points can be marked as
    noise.
    """

    eps: schema_field(
        optimizer_float_field(gt=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.5,
            "lower_bound": 0.1,
            "upper_bound": 2.0,
        },
        description=MultilingualString(
            en="Maximum distance between two samples to be considered neighbours.",
            es="Distancia máxima entre dos muestras para considerarlas vecinas.",
        ),
        alias=MultilingualString(en="Eps", es="Eps"),
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
            en="Minimum samples in a neighbourhood for a point to be core.",
            es="Mínimo de muestras en una vecindad para que un punto sea central.",
        ),
        alias=MultilingualString(en="Min samples", es="Mínimo de muestras"),
    )  # type: ignore
    metric: schema_field(
        enum_field(["euclidean", "manhattan", "cosine"]),
        "euclidean",
        description=MultilingualString(
            en="Distance metric used by DBSCAN.",
            es="Métrica de distancia usada por DBSCAN.",
        ),
        alias=MultilingualString(en="Metric", es="Métrica"),
    )  # type: ignore


class DBSCANClustering(SklearnLikeClusterer, _DBSCAN):
    """DBSCAN clustering model for the Models module.

    DBSCAN is a density-based unsupervised algorithm that discovers clusters
    without requiring the number of clusters in advance. It is useful when
    groups have irregular shapes and when noise or outliers should be identified
    explicitly. Noise samples are labelled as ``-1`` by scikit-learn.

    Key hyperparameters include ``eps`` (the neighbourhood radius),
    ``min_samples`` (minimum points required to form a dense region), and
    ``metric`` (distance function). The implementation wraps scikit-learn's
    ``DBSCAN`` estimator.

    References
    ----------
    - [1] Ester, M., Kriegel, H.-P., Sander, J., & Xu, X. (1996).
           "A density-based algorithm for discovering clusters in large spatial
           databases with noise."
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html
    """

    SCHEMA = DBSCANClusteringSchema
    DISPLAY_NAME = MultilingualString(en="DBSCAN", es="DBSCAN")
    DESCRIPTION = MultilingualString(
        en="Density-based clustering that can identify noise points.",
        es="Clustering basado en densidad que puede identificar puntos de ruido.",
    )
    COLOR = "#7E57C2"
    ICON = "Radar"

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
        """Return DBSCAN post-fit attributes for the converter report."""
        import numpy as np

        n_noise = int(np.sum(self._labels == -1))
        return {"n_noise_points": n_noise} if n_noise > 0 else {}
