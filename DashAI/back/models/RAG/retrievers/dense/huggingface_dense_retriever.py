from abc import abstractmethod

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import DenseRetriever

METRICS = ["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]


class HuggingFaceDenseRetriever(DenseRetriever):
    FLAGS: list[str] = ["abstract", "huggingface"]
    DISPLAY_NAME: str = MultilingualString(
        en="HuggingFace Embedding Retriever",
        es="Recuperador por Embeddings HuggingFace",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using HuggingFace embeddings for similarity search.",
        es="Recuperador denso que usa embeddings HuggingFace para búsqueda por similitud.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def _create_embedding(self) -> HuggingFaceEmbedding:
        raise NotImplementedError

    def init_model(self) -> None:
        embedding = self._create_embedding()
        embedding.load()
        self._init_embedding(embedding)
