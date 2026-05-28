from abc import ABC
from typing import Final, List

from DashAI.back.models.RAG.extra_args_enum import (
    CHUNKS,
    ENV_RAG_PATH,
)
from DashAI.back.models.RAG.retrievers.exceptions import ExtraKwargsMissingError
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel

_COMMON_INFRA_KEYS = {ENV_RAG_PATH, CHUNKS, "persistence"}


class UnitRetriever(RetrieverModel, ABC):
    """Leaf: abstract base for unit retrievers."""

    TYPE: Final[str] = "RetrieverModel"

    REQUIRED_EXTRA_KWARGS: list = [ENV_RAG_PATH, CHUNKS, "persistence"]

    def __init__(self, **kwargs):
        missing = _COMMON_INFRA_KEYS - set(kwargs)
        if missing:
            raise ExtraKwargsMissingError(
                missing_keys=missing,
                retriever_name=self.__class__.__name__,
            )
        if "component_registry" in kwargs:
            kwargs.pop("component_registry")
        self.env_rag_path = kwargs.pop(ENV_RAG_PATH)
        self.chunks = kwargs.pop(CHUNKS)
        self._persistence = kwargs.pop("persistence")
        self._validate_chunks_dict()
        super().__init__(**kwargs)

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
