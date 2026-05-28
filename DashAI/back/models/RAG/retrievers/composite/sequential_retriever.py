from typing import List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    enum_field,
    int_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.enums import RetrievalStrategy
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
            en="Ordered list of child retrievers. Each runs in sequence.",
            es="Lista ordenada de recuperadores hijos. Cada uno se ejecuta en secuencia.",
        ),
    )  # type: ignore

    strategy: schema_field(
        enum_field(enum=[s.value for s in RetrievalStrategy]),
        placeholder=RetrievalStrategy.ACCUMULATE.value,
        description=MultilingualString(
            en=(
                f"'{RetrievalStrategy.ACCUMULATE}': each child contributes chunks "
                f"until the global top_k is reached. "
                f"'{RetrievalStrategy.CASCADE}': the first child retrieves broadly, "
                f"each subsequent child re-ranks and tightens."
            ),
            es=(
                f"'{RetrievalStrategy.ACCUMULATE}': cada hijo contribuye fragmentos "
                f"hasta alcanzar el top_k global. "
                f"'{RetrievalStrategy.CASCADE}': el primer hijo recupera ampliamente, "
                f"cada hijo subsiguiente reordena y ajusta."
            ),
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(ge=1),
        placeholder=10,
        description=MultilingualString(
            en=(
                "In accumulate mode: total chunks to return across all children. "
                "In cascade mode: ignored (last child's top_k determines the count)."
            ),
            es=(
                "En modo acumulación: total de fragmentos a retornar entre todos los hijos. "
                "En modo cascada: ignorado (el top_k del último hijo determina la cuenta)."
            ),
        ),
    )  # type: ignore


class SequentialRetriever(CompositeRetriever):
    SCHEMA = SequentialRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Sequential Retriever",
        es="Recuperador Secuencial",
    )
    DESCRIPTION: str = MultilingualString(
        en="Queries multiple retrievers in sequence. Supports accumulation and cascade re-ranking.",
        es="Consulta múltiples recuperadores en secuencia. Soporta acumulación y reordenamiento en cascada.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.strategy = RetrievalStrategy(self.params.pop("strategy"))
        self.global_top_k = self.params.pop("top_k")
        self._validate()

    def _validate(self) -> None:
        if len(self._children) == 0:
            return

        children_k = [c.retrieval_top_k for c in self._children]

        if self.strategy == RetrievalStrategy.ACCUMULATE:
            max_child_k = max(children_k)
            if self.global_top_k < max_child_k:
                raise CompositeValidationError(
                    f"Accumulate mode requires global_top_k ({self.global_top_k}) "
                    f">= max child top_k ({max_child_k})."
                )

        elif self.strategy == RetrievalStrategy.CASCADE:
            if len(self._children) < 2:
                raise CompositeValidationError(
                    "Cascade mode requires at least 2 children."
                )
            for i, child in enumerate(self._children):
                if not isinstance(child, UnitRetriever):
                    raise UnitRetrieverChildError(
                        child_class=child.__class__.__name__,
                        strategy=self.strategy.value,
                    )
            for i in range(1, len(children_k)):
                if children_k[i] >= children_k[i - 1]:
                    raise CompositeValidationError(
                        f"Cascade requires strictly decreasing top_k. "
                        f"Child {i} top_k={children_k[i]} >= "
                        f"child {i - 1} top_k={children_k[i - 1]}"
                    )

    def retrieve(self, query, **kwargs) -> List[Chunk]:
        if self.strategy == RetrievalStrategy.ACCUMULATE:
            return self._retrieve_accumulate(query, **kwargs)
        return self._retrieve_cascade(query, **kwargs)

    def _retrieve_accumulate(self, query, **kwargs) -> List[Chunk]:
        seen_ids = set()
        results = []
        remaining = self.global_top_k

        for child in self._children:
            if remaining <= 0:
                break
            child_results = child.retrieve(query, **kwargs)
            for chunk in child_results:
                cid = chunk.id if hasattr(chunk, "id") else hash(chunk.text)
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    results.append(chunk)
                    remaining -= 1
                    if remaining <= 0:
                        break

        return results

    def _retrieve_cascade(self, query, **kwargs) -> List[Chunk]:
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
        if self.strategy == RetrievalStrategy.ACCUMULATE:
            return self.global_top_k
        if self._children:
            return self._children[-1].retrieval_top_k
        return 1
