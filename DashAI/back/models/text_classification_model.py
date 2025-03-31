from abc import abstractmethod
from typing import Any

from DashAI.back.models.base_model import BaseModel


class TextClassificationModel(BaseModel):
    """Class for models associated to TextClassificationTask."""

    COMPATIBLE_COMPONENTS = ["TextClassificationTask"]

    @abstractmethod
    def save(self, filename: str) -> None:
        """Store an instance of a model.

        filename (Str): Indicates where to store the model,
        if filename is None, this method returns a bytes array with the model.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, filename: str) -> Any:
        """Restores an instance of a model.

        filename (Str): Indicates where the model was stored.
        """
        raise NotImplementedError
