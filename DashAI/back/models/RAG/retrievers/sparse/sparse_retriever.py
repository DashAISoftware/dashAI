from typing import Dict

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever


class SparseRetriever(UnitRetriever):
    """Abstract base for sparse (keyword-based) retrievers.

    Uses term-frequency based representations (e.g. TF-IDF, BM25) for
    document retrieval.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Keyword Retriever",
        es="Recuperador por Palabras Clave",
        pt="Recuperador por Palavras-chave",
        de="Stichwort-Retriever",
        zh="关键词检索器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using term-frequency based representations.",
        es="Recuperador disperso que usa representaciones basadas en"
        " frecuencia de términos.",
        pt="Recuperador disperso que usa representações baseadas em"
        " frequência de termos.",
        de="Sparser Retriever, der auf Termhäufigkeit basierende"
        " Darstellungen verwendet.",
        zh="使用基于词频表示的稀疏检索器。",
    )

    def __init__(self, **kwargs):
        """Initialize the sparse retriever and its load-state flag."""
        super().__init__(**kwargs)
        self._state_loaded = False

    def _rebind_chunk_map(self, stored: Dict[int, Chunk]) -> Dict[int, Chunk] | None:
        """Rebind a persisted row→chunk map to the currently injected chunks.

        A sparse storage folder is content-addressed, so another session over
        the same corpus intentionally loads it. The persisted map however holds
        that session's ``Chunk`` objects, whose database ids differ, so the map
        must be re-pointed at the current chunks: the same ``(document_id,
        document_position)`` with the same text hash, in the current session's
        objects and ids.

        Parameters
        ----------
        stored : Dict[int, Chunk]
            The persisted row→chunk mapping loaded from disk.

        Returns
        -------
        Dict[int, Chunk] | None
            A new map with the same row keys and the current chunks, or ``None``
            when the persisted state does not describe the current corpus (a
            missing position, a different text hash, or a different number of
            chunks). ``None`` forces a refit.
        """
        current: Dict[tuple[int, int], Chunk] = {}
        for document_chunks in self.chunks.values():
            for chunk in document_chunks.values():
                current[(chunk.document_id, chunk.document_position)] = chunk

        rebound: Dict[int, Chunk] = {}
        for row, stored_chunk in stored.items():
            key = (stored_chunk.document_id, stored_chunk.document_position)
            current_chunk = current.get(key)
            if current_chunk is None or current_chunk.hash != stored_chunk.hash:
                return None
            rebound[row] = current_chunk
        if len(rebound) != len(current):
            return None
        covered = {
            (chunk.document_id, chunk.document_position) for chunk in rebound.values()
        }
        if len(covered) != len(current):
            return None
        return rebound
