from abc import ABC, abstractmethod
from typing import Final, List

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel


class CompositeRetriever(RetrieverModel, ABC):
    """
    Composite: abstract base for retrievers that contain child retrievers.

    Implements the Composite role in the Composite design pattern (GoF).
    """

    TYPE: Final[str] = "RetrieverModel"
    FLAGS: list[str] = ["abstract"]
    REQUIRED_EXTRA_KWARGS: list = []

    def __init__(self, **kwargs):
        children_data = kwargs.pop("children")
        if not isinstance(children_data, list):
            raise TypeError(
                f"'children' must be a list, got {type(children_data).__name__}"
            )
        if children_data and not isinstance(children_data[0], RetrieverModel):
            raise TypeError(
                "'children' must contain RetrieverModel instances, "
                f"got {type(children_data[0]).__name__}"
            )
        self._children: List[RetrieverModel] = children_data
        super().__init__(**kwargs)

    def add(self, child: RetrieverModel) -> None:
        self._children.append(child)

    def remove(self, child: RetrieverModel) -> None:
        self._children.remove(child)

    def get_children(self) -> List[RetrieverModel]:
        return list(self._children)

    @abstractmethod
    def retrieve(self, query, **kwargs) -> List[Chunk]:
        raise NotImplementedError

    def score_chunks(self, chunk_ids: List[int], query: str) -> list:
        return []
