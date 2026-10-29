from typing import Dict, List

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

    def _ordered_chunks(self) -> List[Chunk]:
        """Return the chunks in matrix-row order.

        Documents are taken by ascending id and chunks by ascending position, so
        the row order is a property of the corpus rather than of the dict
        insertion order. A matrix written by another session over the same
        corpus therefore lines up row for row.

        Returns
        -------
        List[Chunk]
            Every chunk of every document, in row order.
        """
        return [
            chunk
            for document_id in sorted(self.chunks)
            for _, chunk in sorted(self.chunks[document_id].items())
        ]

    def row_map_for_corpus(self) -> Dict[int, int]:
        """Return the ``row -> chunk id`` map this corpus produces.

        Returns
        -------
        Dict[int, int]
            The map the fitted matrices must be indexed with.
        """
        return {row: chunk.id for row, chunk in enumerate(self._ordered_chunks())}

    def needs_save(self) -> bool:
        """Return whether the fitted state still has to be written to disk.

        ``RetrieverSetupService`` persists a sparse retriever only when this is
        true, so a folder that was just loaded is not rewritten.

        Returns
        -------
        bool
            ``True`` when the state was fitted rather than loaded.
        """
        return not self._state_loaded

    def _row_map_matches_corpus(self, row_map: Dict[int, int]) -> bool:
        """Return whether a persisted ``row -> chunk id`` map fits the corpus.

        The storage folder is content-addressed, so a map written by another
        session over the same corpus is valid here. A folder wired by hand to a
        different corpus, or fitted with a different row order, would otherwise
        resolve rows to the wrong chunk (or fail with a bare ``KeyError`` at
        query time), so the whole mapping is compared, not just the id set.

        Parameters
        ----------
        row_map : Dict[int, int]
            The persisted ``row -> chunk id`` mapping.

        Returns
        -------
        bool
            ``True`` when the map is exactly the one this corpus produces.
        """
        return row_map == self.row_map_for_corpus()
