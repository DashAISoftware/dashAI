from abc import ABC
from typing import Any, Dict, Final, List

from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.retrievers.persistence import (
    DensePersistence,
    SparsePersistence,
)
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel


class UnitRetriever(RetrieverModel, ABC):
    """Leaf: abstract base for unit retrievers."""

    TYPE: Final[str] = "RetrieverModel"
    FLAGS: list[str] = ["abstract"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def inject_infra(
        self,
        env_rag_path: str,
        chunks: Dict[int, Dict[int, Chunk]],
        persistence: Any,
    ) -> None:
        if not isinstance(persistence, (SparsePersistence, DensePersistence)):
            raise TypeError(
                f"Expected SparsePersistence or DensePersistence, "
                f"got {type(persistence).__name__}"
            )
        super().inject_infra(env_rag_path, chunks, persistence)

    def _check_infra(self) -> None:
        """Raise if infrastructure has not been injected."""
        if self._persistence is None:
            raise RuntimeError(
                f"{self.__class__.__name__}: infrastructure not injected. "
                "Call inject_infra() before retrieve()."
            )

    def add(self, child: RetrieverModel) -> None:
        raise TypeError(
            f"{self.__class__.__name__} is a unit retriever and cannot contain children."
        )

    def remove(self, child: RetrieverModel) -> None:
        raise TypeError(
            f"{self.__class__.__name__} is a unit retriever and cannot contain children."
        )

    def get_children(self) -> List[RetrieverModel]:
        return []
