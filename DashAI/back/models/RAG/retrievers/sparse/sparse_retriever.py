from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.retrievers.unit_retriever import UnitRetriever


class SparseRetriever(UnitRetriever):
    DISPLAY_NAME: str = MultilingualString(
        en="Sparse Retriever",
        es="Recuperador Disperso",
    )
    DESCRIPTION: str = MultilingualString(
        en="Sparse retriever using term-frequency based representations.",
        es="Recuperador disperso que usa representaciones basadas en frecuencia de términos.",
    )
