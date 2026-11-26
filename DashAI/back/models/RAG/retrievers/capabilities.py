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
from enum import Enum
from typing import ClassVar, Dict, List, Optional, Tuple

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import RAGRetrieverRerankError


class ScoringChild(Enum):
    """Which child of a composite scorer produces the scores it reports."""

    FIRST = "first"
    LAST = "last"


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

    A composite scorer reports the scores of one of its children, so that child
    must itself be a chunk scorer: ``SCORING_CHILD`` names it (the first or the
    last child). A leaf scorer, or one that scores with its own model, leaves
    it ``None``.
    """

    SCORING_CHILD: ClassVar[Optional[ScoringChild]] = None

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

        Every chunk is scored through the stored chunks it covers: a plain
        chunk through its own id, and a retrieve-then-expand window through the
        ids of all the chunks it spans, keeping the best (lowest) distance. The
        best ``retrieval_top_k`` are kept.

        Args:
            chunks: The candidate pool, in its current order. May be empty.
            query: The query the pool is ranked against.

        Returns:
            At most ``retrieval_top_k`` chunks, best first.

        Raises:
            RAGRetrieverRerankError: If any pool chunk could not be scored (no
                id, or ids the scorer does not hold), which means the scorer's
                index does not hold the pool.
        """
        if not chunks:
            return []
        covered = self._covered_ids(chunks)
        distances = self._distances(covered, query)
        scored: List[Tuple[float, int, Chunk]] = []
        unscorable = 0
        for order, chunk in enumerate(chunks):
            best = _best_distance(covered[order], distances)
            if best is None:
                unscorable += 1
            else:
                scored.append((best, order, chunk))
        if unscorable:
            raise RAGRetrieverRerankError(
                f"{type(self).__name__} could not score {unscorable} of the "
                f"{len(chunks)} pooled chunks; its index does not hold them."
            )
        scored.sort(key=_distance_then_order)
        ranked = [entry[2] for entry in scored]
        return ranked[: self.retrieval_top_k]

    def _covered_ids(self, chunks: List[Chunk]) -> List[List[int]]:
        """Return, per pool chunk, the stored chunk ids it is scored through.

        Args:
            chunks: The candidate pool.

        Returns:
            One id list per chunk: the chunk's own id, or for an expanded
            window the ids of every stored chunk at its ``source_positions``.
            A scorer that has no chunk store at all (``chunks`` is ``None`` or
            absent) cannot resolve a window, so it ranks it by its own id, the
            id of the first chunk it covers.

        Raises:
            RAGRetrieverRerankError: If the scorer has a chunk store and none of
                a window's ``source_positions`` resolves in it.
        """
        corpus = getattr(self, "chunks", None)
        covered: List[List[int]] = []
        for chunk in chunks:
            positions = getattr(chunk, "source_positions", None)
            if not positions or corpus is None:
                covered.append([] if chunk.id is None else [chunk.id])
                continue
            ids: List[int] = []
            for stored in corpus.get(chunk.document_id, {}).values():
                if stored.id is not None and stored.document_position in positions:
                    ids.append(stored.id)
            if not ids:
                raise RAGRetrieverRerankError(
                    f"{type(self).__name__} could not resolve the chunks of a "
                    f"window of document {chunk.document_id} at positions "
                    f"{sorted(positions)} in its chunk store."
                )
            covered.append(ids)
        return covered

    def _distances(self, covered: List[List[int]], query: str) -> Dict[int, float]:
        """Score every distinct covered id once.

        Args:
            covered: The per-chunk covered id lists.
            query: The query the ids are scored against.

        Returns:
            The distance of each id the scorer holds.
        """
        unique_ids = list(
            dict.fromkeys(chunk_id for ids in covered for chunk_id in ids)
        )
        if not unique_ids:
            return {}
        return dict(self.score_chunks(unique_ids, query))


def _best_distance(ids: List[int], distances: Dict[int, float]) -> float | None:
    """Return the lowest distance among *ids*, or ``None`` if none is scored."""
    best = None
    for chunk_id in ids:
        distance = distances.get(chunk_id)
        if distance is not None and (best is None or distance < best):
            best = distance
    return best


def _distance_then_order(entry: Tuple[float, int, Chunk]) -> Tuple[float, int]:
    """Sort key: ascending distance, ties kept in pool order."""
    return entry[0], entry[1]
