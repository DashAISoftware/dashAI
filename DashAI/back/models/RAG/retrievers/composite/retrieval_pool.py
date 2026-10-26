"""In-memory iterative retrieval pool for the LLM-evaluated retrievers.

The pool accumulates the chunks returned by successive retrieval rounds and lets
the language model steer it explicitly: chunks can be *requested* (included even
when no retriever returned them) or *discarded* (excluded even when a later
round returns them). States are overwritable — the last action applied to a
chunk wins — and the pool is capped at ``max_chunks`` when materialized.

The class is pure and in-memory: it never persists anything and holds no
reference to the database.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.composite.retrieval_context import (
    RetrievalContext,
)
from DashAI.back.models.RAG.retrievers.retrieval_contracts import (
    DISCARD_KEY,
    REQUEST_CHUNKS_KEY,
)

#: Chunk identity used by the pool: ``(document_id, document_position)``.
ChunkKey = Tuple[int, int]


class RetrievalPool:
    """Ordered, requestable and discardable chunk pool.

    Parameters
    ----------
    max_chunks : int
        Maximum number of chunks ``materialize()`` returns.
    context : RetrievalContext
        Document/corpus knowledge used to resolve chunks explicitly requested by
        the language model that no retriever has returned yet.
    """

    def __init__(self, max_chunks: int, context: RetrievalContext) -> None:
        self._max_chunks = max_chunks
        self._context = context
        self._order: List[ChunkKey] = []
        self._chunks: Dict[ChunkKey, Chunk] = {}
        self._requested: Set[ChunkKey] = set()
        self._requested_batches: List[List[ChunkKey]] = []
        self._discarded: Set[ChunkKey] = set()

    @staticmethod
    def _key(chunk: Chunk) -> ChunkKey:
        """Build the pool identity key for a chunk.

        Parameters
        ----------
        chunk : Chunk
            Chunk to identify.

        Returns
        -------
        ChunkKey
            ``(document_id, document_position)``.
        """
        return (chunk.document_id, chunk.document_position)

    def _remember(self, chunk: Chunk) -> None:
        """Add ``chunk`` the first time it is seen, preserving insertion order.

        Parameters
        ----------
        chunk : Chunk
            Chunk to add when its identity has not been seen before.
        """
        key = self._key(chunk)
        if key not in self._chunks:
            self._chunks[key] = chunk
            self._order.append(key)

    def add(self, chunks: Iterable[Chunk]) -> None:
        """Add every unseen chunk of ``chunks``, preserving first-seen order.

        Parameters
        ----------
        chunks : Iterable[Chunk]
            Chunks returned by a retrieval round. Duplicates are ignored.
        """
        for chunk in chunks:
            self._remember(chunk)

    def _resolve(self, document_id: int, position: int) -> Chunk | None:
        """Return a chunk from the pool or the corpus.

        Parameters
        ----------
        document_id : int
            Document id to look up.
        position : int
            Zero-based chunk position to look up.

        Returns
        -------
        Chunk | None
            The known chunk, or ``None`` when it does not exist.
        """
        key = (document_id, position)
        chunk = self._chunks.get(key)
        if chunk is not None:
            return chunk
        return self._context.get_chunk(document_id, position)

    def request(self, mapping: Dict[int, List[int]]) -> List[str]:
        """Include explicitly requested chunks in the pool.

        Unknown positions are skipped instead of aborting the whole request: the
        model may hallucinate a position, but the valid operations must still be
        applied. The invalid ones are reported as drop messages.

        Parameters
        ----------
        mapping : Dict[int, List[int]]
            Document id to chunk positions requested by the model.

        Returns
        -------
        List[str]
            One human-readable message per requested position that does not
            exist in the retrieval corpus.
        """
        drops: List[str] = []
        batch: List[ChunkKey] = []
        for document_id, positions in mapping.items():
            for position in positions:
                chunk = self._resolve(document_id, position)
                if chunk is None:
                    drops.append(
                        f"Dropped '{REQUEST_CHUNKS_KEY}' position {position} of "
                        f"document {document_id}: it does not exist in the "
                        "retrieval corpus."
                    )
                    continue
                key = (document_id, position)
                self._remember(chunk)
                self._requested.add(key)
                self._discarded.discard(key)
                batch.append(key)
        self._requested_batches.append(batch)
        return drops

    def discard(self, mapping: Dict[int, List[int]]) -> List[str]:
        """Exclude discarded chunks from the pool (last state wins).

        Unknown positions are skipped instead of aborting the whole discard: the
        model may hallucinate a position, but the valid operations must still be
        applied. The invalid ones are reported as drop messages.

        Parameters
        ----------
        mapping : Dict[int, List[int]]
            Document id to chunk positions to exclude.

        Returns
        -------
        List[str]
            One human-readable message per discarded position that does not
            exist in the retrieval corpus.
        """
        drops: List[str] = []
        for document_id, positions in mapping.items():
            for position in positions:
                chunk = self._resolve(document_id, position)
                if chunk is None:
                    drops.append(
                        f"Dropped '{DISCARD_KEY}' position {position} of "
                        f"document {document_id}: it does not exist in the "
                        "retrieval corpus."
                    )
                    continue
                key = (document_id, position)
                self._discarded.add(key)
                self._requested.discard(key)
        return drops

    def materialize(self) -> List[Chunk]:
        """Return the pool: newest requested chunks first, then the rest.

        Requested chunks are emitted newest-batch first, preserving each
        batch's order and deduplicating repeated keys. Every remaining
        non-requested, non-discarded chunk follows in first-seen order. The
        result is truncated to ``max_chunks``.

        Returns
        -------
        List[Chunk]
            The ordered, capped pool.
        """
        ordered: List[Chunk] = []
        emitted: Set[ChunkKey] = set()
        for batch in reversed(self._requested_batches):
            for key in batch:
                if key not in self._requested or key in emitted:
                    continue
                ordered.append(self._chunks[key])
                emitted.add(key)
        for key in self._order:
            if key in self._requested or key in self._discarded:
                continue
            ordered.append(self._chunks[key])
        return ordered[: self._max_chunks]

    def size(self) -> int:
        """Return the number of chunks ``materialize()`` would yield.

        Returns
        -------
        int
            The capped pool size.
        """
        return len(self.materialize())

    def discarded_count(self) -> int:
        """Return how many tracked chunks are currently discarded.

        Only chunks already seen by the pool count: discarding an unseen
        position does not occupy a pool slot, so it does not need a replacement
        retrieval.

        Returns
        -------
        int
            Number of tracked chunks currently discarded.
        """
        count = 0
        for key in self._order:
            if key in self._discarded:
                count += 1
        return count
