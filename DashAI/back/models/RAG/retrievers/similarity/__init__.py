"""Distance metrics a vector retriever ranks its chunks with."""

from DashAI.back.models.RAG.retrievers.similarity.base_similarity_metric import (
    BaseSimilarityMetric,
    require_similarity_metric,
)
from DashAI.back.models.RAG.retrievers.similarity.cosine_similarity import (
    CosineSimilarity,
)
from DashAI.back.models.RAG.retrievers.similarity.euclidean_similarity import (
    EuclideanSimilarity,
)
from DashAI.back.models.RAG.retrievers.similarity.manhattan_similarity import (
    ManhattanSimilarity,
)

__all__ = [
    "BaseSimilarityMetric",
    "CosineSimilarity",
    "EuclideanSimilarity",
    "ManhattanSimilarity",
    "require_similarity_metric",
]
