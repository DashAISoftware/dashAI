"""Capability interfaces a retriever opts into by inheritance.

A capability is a plain ABC mixin, not a registered component base type. A
retriever has a capability when its class inherits the interface, and the
component registry resolves a schema field declared with that interface as its
parent (``component_field(parent="ChunkScorer")``) by walking the class MRO. So
the choice of which components a field offers is made by the class hierarchy
and never by a list of names: a new retriever that inherits a capability shows
up wherever that capability is required, with no other change.

Adding a capability means adding one ABC here, inheriting it in the retrievers
that satisfy its contract, and declaring it as the parent of the schema fields
that need it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from DashAI.back.models.RAG.documents import Chunk


class ChunkScorer(ABC):
    """Capability: scores a candidate pool of chunks against a query.

    A retriever is a chunk scorer when its :meth:`score_chunks` gives every
    candidate it holds a distance from the query, comparable across the
    candidates it scores. Scorers can therefore reorder a pool they did not
    retrieve, which is what :meth:`rerank_chunks` does.

    A retriever that fuses several children by averaging their scores is not a
    scorer: each child may score a different subset of the candidates, so the
    averages are not comparable and a chunk no child scored has no score at
    all. Such a retriever does not inherit this interface.
    """

    @abstractmethod
    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        """Score chunks against a query.

        Args:
            chunk_ids: Chunk IDs to score.
            query: The query the chunks are scored against.

        Returns:
            ``(chunk_id, distance)`` tuples sorted ascending (lower is more
            relevant). Candidates the retriever does not hold are omitted.
        """
        raise NotImplementedError

    def rerank_chunks(self, chunks: List[Chunk], query: str) -> List[Chunk]:
        """Order an already-retrieved candidate pool by this scorer's distance.

        The pool's chunk ids are scored with :meth:`score_chunks`, and the best
        ``retrieval_top_k`` are kept. Chunks the scorer does not score (no
        id, or an id it does not hold) keep their pool order after the scored
        ones, so a partial score never drops a candidate.

        Args:
            chunks: The candidate pool, in its current order. May be empty.
            query: The query the pool is ranked against.

        Returns:
            At most ``retrieval_top_k`` chunks, best first.
        """
        if not chunks:
            return []
        scored = self.score_chunks(
            [chunk.id for chunk in chunks if chunk.id is not None], query
        )
        by_id = {chunk.id: chunk for chunk in chunks if chunk.id is not None}
        ranked = [by_id[chunk_id] for chunk_id, _ in scored if chunk_id in by_id]
        scored_ids = {chunk.id for chunk in ranked}
        ranked += [chunk for chunk in chunks if chunk.id not in scored_ids]
        return ranked[: self.retrieval_top_k]
