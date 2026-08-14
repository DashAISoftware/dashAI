from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever


class SparseRetriever(UnitRetriever):
    """Abstract base for sparse (keyword-based) retrievers.

    Uses term-frequency based representations (e.g. TF-IDF, BM25) for
    document retrieval.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Keyword Retriever",
        es="Recuperador por Palabras Clave",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using term-frequency based representations.",
        es="Recuperador disperso que usa representaciones basadas en"
        " frecuencia de términos.",
    )
