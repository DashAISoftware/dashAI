"""Manhattan (L1) distance between two vectors."""

from typing import ClassVar

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.retrievers.similarity.base_similarity_metric import (
    BaseSimilarityMetric,
)


# Takes no parameters. A docstring here would become the schema description
# the frontend shows, so the class carries none.
class ManhattanSimilaritySchema(BaseSchema):
    pass


class ManhattanSimilarity(BaseSimilarityMetric):
    """Manhattan distance: the sum of the absolute differences of the vectors."""

    SCHEMA = ManhattanSimilaritySchema
    SKLEARN_METRIC: ClassVar[str] = "manhattan"
    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Manhattan distance",
        es="Distancia Manhattan",
        pt="Distância de Manhattan",
        de="Manhattan-Distanz",
        zh="曼哈顿距离",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en="Manhattan distance: the sum of the absolute differences per dimension.",
        es="Distancia Manhattan: suma de las diferencias absolutas por dimensión.",
        pt="Distância de Manhattan: soma das diferenças absolutas por dimensão.",
        de="Manhattan-Distanz: Summe der absoluten Differenzen je Dimension.",
        zh="曼哈顿距离：向量之间各维度绝对差之和。",
    )
