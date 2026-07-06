from typing import List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.exceptions import (
    CompositeValidationError,
    UnitRetrieverChildError,
)
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever


class SequentialRetrieverSchema(BaseSchema):
    children: schema_field(
        list_field(component_field(parent="RetrieverModel"), min_items=2),
        placeholder=[],
        description=MultilingualString(
            en="Ordered list of child retrievers. The first child retrieves broadly; "
            "each subsequent child re-ranks and tightens the results.",
            es="Lista ordenada de recuperadores hijos. El primero recupera ampliamente; "
            "cada hijo subsiguiente reordena y ajusta los resultados.",
        ),
    )  # type: ignore


class SequentialRetriever(CompositeRetriever):
    FLAGS: list[str] = ["composite", "sequential"]
    SCHEMA = SequentialRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Sequential Retriever",
        es="Recuperador Secuencial",
    )
    DESCRIPTION: str = MultilingualString(
        en="Queries multiple retrievers in sequence, re-ranking at each step.",
        es="Consulta múltiples recuperadores en secuencia, reordenando en cada paso.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate()

    def _validate(self) -> None:
        children = getattr(self, "_children", [])
        if len(children) < 2:
            return

        children_k = [c.retrieval_top_k for c in children]

        for _i, child in enumerate(children):
            if not isinstance(child, UnitRetriever):
                raise UnitRetrieverChildError(
                    child_class=child.__class__.__name__,
                    strategy="cascade",
                )

        for i in range(1, len(children_k)):
            if children_k[i] >= children_k[i - 1]:
                raise CompositeValidationError(
                    f"Cascade requires strictly decreasing top_k. "
                    f"Child {i} top_k={children_k[i]} >= "
                    f"child {i - 1} top_k={children_k[i - 1]}"
                )

    def retrieve(self, query, **kwargs) -> List[Chunk]:
        first = self._children[0]
        results = first.retrieve(query, **kwargs)

        for child in self._children[1:]:
            chunk_ids = [c.id for c in results]
            scored = child.score_chunks(chunk_ids, query)
            scored = scored[: child.retrieval_top_k]
            id_to_chunk = {c.id: c for c in results}
            results = [id_to_chunk[cid] for cid, _ in scored]

        return results

    @property
    def retrieval_top_k(self) -> int:
        if self._children:
            return self._children[-1].retrieval_top_k
        return 1
