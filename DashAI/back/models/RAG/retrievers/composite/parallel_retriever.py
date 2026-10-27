from typing import Any, Dict, List, Tuple

from DashAI.back.core.schema_fields import (
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
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    RetrievalExpansionSchema,
    prefer_wider_chunk,
)
from DashAI.back.models.RAG.retrievers.trace_utils import retriever_trace


class ParallelRetrieverSchema(RetrievalExpansionSchema):
    """Schema for :class:`ParallelRetriever`.

    Attributes:
        children: List of at least 2 child retrievers queried in parallel.
        merge_strategy: Strategy for merging results
            (:attr:`MergeStrategy` values).
    """

    children: schema_field(
        list_field(component_field(parent="BaseRetriever"), min_items=2),
        placeholder=[],
        description=MultilingualString(
            en="List of child retrievers queried in parallel.",
            es="Lista de recuperadores hijos consultados en paralelo.",
            pt="Lista de recuperadores filhos consultados em paralelo.",
            de="Liste der parallel abgefragten Kind-Retriever.",
            zh="并行查询的子检索器列表。",
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
    """Queries multiple retrievers in parallel and merges their results.

    Results are deduplicated by ``(document_id, document_position)``.
    """

    SCHEMA = ParallelRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Parallel Retriever",
        es="Recuperador Paralelo",
        pt="Recuperador Paralelo",
        de="Paralleler Retriever",
        zh="并行检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Queries multiple retrievers in parallel and merges their results.",
        es="Consulta múltiples recuperadores en paralelo y fusiona sus resultados.",
        pt="Consulta vários recuperadores em paralelo e mescla seus resultados.",
        de="Fragt mehrere Retriever parallel ab und führt ihre Ergebnisse zusammen.",
        zh="并行查询多个检索器并合并其结果。",
    )

    REPRESENTATION = MultilingualString(
        en="merge {merge_strategy}",
        es="fusión {merge_strategy}",
        pt="mesclagem {merge_strategy}",
        de="Zusammenführung {merge_strategy}",
        zh="合并 {merge_strategy}",
    )

    @classmethod
    def _get_main_parameters(cls) -> Dict[str, str]:
        """Return the merge-strategy path."""
        return {"merge_strategy": "merge_strategy"}

    def __init__(self, **kwargs):
        """Initialize the parallel retriever with a merge strategy.

        Args:
            **kwargs: Must contain ``children`` and ``merge_strategy``
                keys.
        """
        super().__init__(**kwargs)
        self.merge_strategy = MergeStrategy(self.params.pop("merge_strategy"))

    @property
    def retrieval_top_k(self) -> int:
        """Return the sum of all children's top_k.

        Returns:
            Total number of chunks the parallel retriever may return.
        """
        return sum(c.retrieval_top_k for c in self._children)

    def retrieve(self, query, **kwargs) -> Tuple[List[Chunk], Dict[str, Any]]:
        """Retrieve chunks from all children in parallel and merge.

        Args:
            query: The search query string.
            **kwargs: Additional retrieval parameters forwarded to each
                child.

        Returns:
            A ``(chunks, trace)`` tuple: the deduplicated, merged list of
            :class:`Chunk` instances and a trace node whose ``children`` list
            holds each child's own trace node, in child order.
        """
        all_child_results = []
        child_nodes = []
        for child in self._children:
            child_chunks, child_node = child.retrieve(query, **kwargs)
            all_child_results.append(child_chunks)
            child_nodes.append(child_node)

        total_k = sum(c.retrieval_top_k for c in self._children)

        if self.merge_strategy == MergeStrategy.ROUND_ROBIN:
            merged = self._merge_round_robin(all_child_results, total_k)
        else:
            merged = self._merge_interleave(all_child_results, total_k)
        merged = self._apply_retrieval_expansion(merged)
        return merged, retriever_trace(self, merged, children=child_nodes)

    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Aggregate chunk scores across all children.

        Each child scores the chunks independently, then all scores
        for the same chunk are averaged. Results sorted by distance
        (ascending = more relevant). Chunks that no child scored
        are omitted.

        Args:
            chunk_ids: List of chunk IDs to score.
            query: The search query string.

        Returns:
            A list of ``(chunk_id, average_distance)`` tuples sorted by
            distance.
        """
        if not chunk_ids or not self._children:
            return []

        accumulator = {cid: [] for cid in chunk_ids}
        for child in self._children:
            for cid, dist in child.score_chunks(chunk_ids, query):
                accumulator[cid].append(dist)

        merged = []
        for cid, dists in accumulator.items():
            if dists:
                merged.append((cid, sum(dists) / len(dists)))
        merged.sort(key=lambda pair: pair[1])
        return merged

    @staticmethod
    def _chunk_key(chunk: Chunk) -> Tuple[int, int]:
        """Build a hashable dedup key from document_id and position.

        Both values are ints — see Chunk model definition.

        Args:
            chunk: The chunk to generate a key for.

        Returns:
            A ``(document_id, document_position)`` tuple.
        """
        return (chunk.document_id, chunk.document_position)

    def _merge_round_robin(
        self, child_results_list: List[List[Chunk]], total_k: int
    ) -> List[Chunk]:
        """Merge results using round-robin alternation.

        Takes turns picking from each child's result list. A repeated
        ``(document_id, document_position)`` key does not add a new entry: the
        chunk covering more document positions replaces the earlier one in
        place, so a widened window is never dropped in favour of the plain chunk
        or narrower window anchored on the same position.

        Args:
            child_results_list: Results from each child retriever.
            total_k: Maximum number of chunks to return.

        Returns:
            A deduplicated list of up to *total_k* chunks.
        """
        results: List[Chunk] = []
        seen_positions: Dict[Tuple[int, int], int] = {}
        max_len = max(len(r) for r in child_results_list) if child_results_list else 0

        for i in range(max_len):
            for child_results in child_results_list:
                if i < len(child_results):
                    chunk = child_results[i]
                    key = self._chunk_key(chunk)
                    position = seen_positions.get(key)
                    if position is not None:
                        results[position] = prefer_wider_chunk(results[position], chunk)
                        continue
                    seen_positions[key] = len(results)
                    results.append(chunk)
                    if len(results) >= total_k:
                        return results
        return results

    def _merge_interleave(
        self, child_results_list: List[List[Chunk]], total_k: int
    ) -> List[Chunk]:
        """Merge results by interleaving in child order.

        Concatenates each child's list in order. A repeated
        ``(document_id, document_position)`` key replaces the earlier entry in
        place with the chunk covering more document positions, exactly like
        :meth:`_merge_round_robin`.

        Args:
            child_results_list: Results from each child retriever.
            total_k: Maximum number of chunks to return.

        Returns:
            A deduplicated list of up to *total_k* chunks.
        """
        results: List[Chunk] = []
        seen_positions: Dict[Tuple[int, int], int] = {}

        for child_results in child_results_list:
            for chunk in child_results:
                key = self._chunk_key(chunk)
                position = seen_positions.get(key)
                if position is not None:
                    results[position] = prefer_wider_chunk(results[position], chunk)
                    continue
                seen_positions[key] = len(results)
                results.append(chunk)
                if len(results) >= total_k:
                    return results
        return results
