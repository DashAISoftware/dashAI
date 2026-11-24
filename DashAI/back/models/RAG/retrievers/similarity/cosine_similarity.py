"""Cosine distance between two vectors."""

from typing import ClassVar

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.retrievers.similarity.base_similarity_metric import (
    BaseSimilarityMetric,
)


# Takes no parameters. A docstring here would become the schema description
# the frontend shows, so the class carries none.
class CosineSimilaritySchema(BaseSchema):
    pass


class CosineSimilarity(BaseSimilarityMetric):
    """Cosine distance: one minus the cosine of the angle between two vectors.

    The distance compares only the direction of the vectors, so their length
    does not change the ranking.
    """

    SCHEMA = CosineSimilaritySchema
    SKLEARN_METRIC: ClassVar[str] = "cosine"
    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Cosine distance",
        es="Distancia del coseno",
        pt="Distância do cosseno",
        de="Kosinus-Distanz",
        zh="余弦距离",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en="Cosine distance: compares the direction of the vectors, not their length.",
        es="Distancia del coseno: compara solo la dirección de los vectores.",
        pt="Distância do cosseno: compara a direção dos vetores, não o comprimento.",
        de="Kosinus-Distanz: vergleicht die Richtung der Vektoren, nicht ihre Länge.",
        zh="余弦距离：比较向量的方向并忽略其长度。",
    )
