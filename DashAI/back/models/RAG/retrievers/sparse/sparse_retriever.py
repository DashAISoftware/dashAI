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
    CATEGORY: MultilingualString = MultilingualString(
        en="Keyword retrievers",
        es="Recuperadores por palabras clave",
        pt="Recuperadores por palavras-chave",
        de="Stichwort-Retriever",
        zh="关键词检索器",
    )

    def __init__(self, **kwargs):
        """Initialize the sparse retriever and its load-state flag."""
        super().__init__(**kwargs)
        self._state_loaded = False

    def _chunks_by_id(self) -> Dict[int, Chunk]:
        """Return the chunks the retriever was given, keyed by chunk id.

        The saved row maps hold only chunk ids, so the chunk text is read
        from the chunk set rather than kept in the retriever files.

        Returns
        -------
        Dict[int, Chunk]
            Every chunk of every document, keyed by ``Chunk.id``.
        """
        return {
            chunk.id: chunk
            for document_chunks in self.chunks.values()
            for chunk in document_chunks.values()
        }

    def _row_map_matches_chunks(self, row_map: Dict[int, int]) -> bool:
        """Return whether a persisted ``row -> chunk id`` map fits the corpus.

        The storage folder is content-addressed, so a map written by another
        session over the same corpus is valid here. A folder wired by hand to a
        different corpus would otherwise load a map whose ids are missing from
        ``_chunk_lookup`` and fail later with a bare ``KeyError`` at query time.

        Parameters
        ----------
        row_map : Dict[int, int]
            The persisted ``row -> chunk id`` mapping.

        Returns
        -------
        bool
            ``True`` when the map covers exactly the injected chunks.
        """
        return set(row_map.values()) == set(self._chunks_by_id())
