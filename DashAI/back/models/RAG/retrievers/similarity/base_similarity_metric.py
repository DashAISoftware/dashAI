"""Base class for the distance metrics the vector retrievers rank chunks with."""

from abc import ABC
from typing import Any, ClassVar, Final

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import pairwise_distances

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.utils import MultilingualString


class BaseSimilarityMetric(ConfigObject, ABC):
    """Base class for the distance metrics retrievers rank chunks with.

    A metric measures how far each stored vector lies from a query vector.
    Lower distances are more relevant, so retrievers sort in ascending order.
    Each subclass names the scikit-learn metric it delegates to in
    ``SKLEARN_METRIC`` and declares its own schema and display names.
    """

    TYPE: Final[str] = "SimilarityMetric"
    SKLEARN_METRIC: ClassVar[str]
    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Similarity metric",
        es="Métrica de similitud",
        pt="Métrica de similaridade",
        de="Ähnlichkeitsmetrik",
        zh="相似度度量",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en="Distance metric used to rank chunks.",
        es="Métrica de distancia usada para ordenar los fragmentos.",
        pt="Métrica de distância usada para ordenar os fragmentos.",
        de="Distanzmetrik zum Sortieren der Chunks.",
        zh="用于对文本块排序的距离度量。",
    )

    def distances(
        self, queries: np.ndarray | csr_matrix, vectors: np.ndarray | csr_matrix
    ) -> np.ndarray:
        """Return the distance of every query to every vector.

        Parameters
        ----------
        queries : np.ndarray | csr_matrix
            Query vectors, one per row.
        vectors : np.ndarray | csr_matrix
            Stored vectors, one per row.

        Returns
        -------
        np.ndarray
            A ``(len(queries), len(vectors))`` matrix of distances.
        """
        return pairwise_distances(queries, vectors, metric=self.SKLEARN_METRIC)


def require_similarity_metric(metric: Any) -> BaseSimilarityMetric:
    """Return ``metric`` when it is a similarity metric component instance.

    Parameters
    ----------
    metric : Any
        The value a retriever received for its metric parameter.

    Returns
    -------
    BaseSimilarityMetric
        The same instance, unchanged.

    Raises
    ------
    TypeError
        If ``metric`` is not a :class:`BaseSimilarityMetric` instance, for
        example the bare metric name a legacy configuration stored.
    """
    if not isinstance(metric, BaseSimilarityMetric):
        raise TypeError(
            f"Expected BaseSimilarityMetric instance, got {type(metric).__name__}"
        )
    return metric
