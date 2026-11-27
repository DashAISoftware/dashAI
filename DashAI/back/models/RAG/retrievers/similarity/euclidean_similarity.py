"""Euclidean (L2) distance between two vectors."""

from typing import ClassVar

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.retrievers.similarity.base_similarity_metric import (
    BaseSimilarityMetric,
)


# Takes no parameters. A docstring here would become the schema description
# the frontend shows, so the class carries none.
class EuclideanSimilaritySchema(BaseSchema):
    pass


class EuclideanSimilarity(BaseSimilarityMetric):
    """Euclidean distance: the straight-line distance between two vectors."""

    SCHEMA = EuclideanSimilaritySchema
    SKLEARN_METRIC: ClassVar[str] = "euclidean"
    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Euclidean distance",
        es="Distancia euclidiana",
        pt="Distância euclidiana",
        de="Euklidische Distanz",
        zh="欧几里得距离",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en="Euclidean distance: the straight-line distance between the vectors.",
        es="Distancia euclidiana: la distancia en línea recta entre los vectores.",
        pt="Distância euclidiana: a distância em linha reta entre os vetores.",
        de="Euklidische Distanz: der direkte Abstand zwischen den Vektoren.",
        zh="欧几里得距离：向量之间的直线距离。",
    )
