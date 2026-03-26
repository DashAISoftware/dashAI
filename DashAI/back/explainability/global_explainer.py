from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final, List, Tuple

from DashAI.back.config_object import ConfigObject
from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from datasets import DatasetDict


class BaseGlobalExplainer(ConfigObject, ABC):
    """Base class for global explainers."""

    TYPE: Final[str] = "GlobalExplainer"

    def __init__(self, model: BaseModel) -> None:
        self.model = model

    @abstractmethod
    def explain(self, dataset: Tuple["DatasetDict", "DatasetDict"]) -> dict:
        raise NotImplementedError

    @abstractmethod
    def plot(self, explanation: dict) -> List[dict]:
        raise NotImplementedError
