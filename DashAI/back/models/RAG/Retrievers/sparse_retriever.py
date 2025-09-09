
from DashAI.back.models.RAG.Retrievers.retriever_model import RetrieverModel


class SparseRetriever(RetrieverModel):
    """
    Abstract class for sparse retrievers.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
