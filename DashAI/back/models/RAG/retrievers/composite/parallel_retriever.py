from typing import List, Tuple

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    enum_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.enums import MergeStrategy


class ParallelRetrieverSchema(BaseSchema):
    children: schema_field(
        list_field(component_field(parent="RetrieverModel"), min_items=2),
        placeholder=[],
        description=MultilingualString(
            en="List of child retrievers queried in parallel.",
            es="Lista de recuperadores hijos consultados en paralelo.",
        ),
    )  # type: ignore

    merge_strategy: schema_field(
        enum_field(enum=[s.value for s in MergeStrategy]),
        placeholder=MergeStrategy.ROUND_ROBIN.value,
        description=MultilingualString(
            en=(
                f"'{MergeStrategy.ROUND_ROBIN.value}': alternates results"
                f" from each retriever. "
                f"'{MergeStrategy.INTERLEAVE.value}': merges preserving"
                f" internal order."
            ),
            es=(
                f"'{MergeStrategy.ROUND_ROBIN.value}': alterna resultados"
                f" de cada recuperador. "
                f"'{MergeStrategy.INTERLEAVE.value}': fusiona preservando"
                f" el orden interno."
            ),
        ),
    )  # type: ignore


class ParallelRetriever(CompositeRetriever):
    FLAGS: list[str] = ["composite", "parallel"]
    SCHEMA = ParallelRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Parallel Retriever",
        es="Recuperador Paralelo",
    )
    DESCRIPTION: str = MultilingualString(
        en="Queries multiple retrievers in parallel and merges their results.",
        es="Consulta múltiples recuperadores en paralelo y fusiona sus resultados.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.merge_strategy = MergeStrategy(self.params.pop("merge_strategy"))

    @property
    def retrieval_top_k(self) -> int:
        return sum(c.retrieval_top_k for c in self._children)

    def retrieve(self, query, **kwargs) -> List[Chunk]:
        all_child_results = []
        for child in self._children:
            all_child_results.append(child.retrieve(query, **kwargs))

        total_k = sum(c.retrieval_top_k for c in self._children)

        if self.merge_strategy == MergeStrategy.ROUND_ROBIN:
            return self._merge_round_robin(all_child_results, total_k)
        return self._merge_interleave(all_child_results, total_k)

    @staticmethod
    def _chunk_key(chunk: Chunk) -> Tuple[str, int]:
        return (chunk.document_id, chunk.document_position)

    def _merge_round_robin(
        self, child_results_list: List[List[Chunk]], total_k: int
    ) -> List[Chunk]:
        results = []
        seen_keys: set[Tuple[str, int]] = set()
        max_len = max(len(r) for r in child_results_list) if child_results_list else 0

        for i in range(max_len):
            for child_results in child_results_list:
                if i < len(child_results):
                    chunk = child_results[i]
                    key = self._chunk_key(chunk)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(chunk)
                        if len(results) >= total_k:
                            return results
        return results

    def _merge_interleave(
        self, child_results_list: List[List[Chunk]], total_k: int
    ) -> List[Chunk]:
        results = []
        seen_keys: set[Tuple[str, int]] = set()

        for child_results in child_results_list:
            for chunk in child_results:
                key = self._chunk_key(chunk)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(chunk)
                    if len(results) >= total_k:
                        return results
        return results
