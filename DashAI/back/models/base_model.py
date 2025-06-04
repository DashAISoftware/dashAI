"""Base Model abstract class."""

from abc import ABCMeta, abstractmethod
from typing import Any, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract class of all machine learning models.

    All models must extend this class and implement save and load methods.
    """

    TYPE: Final[str] = "Model"

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
    
    @abstractmethod
    def convert_format(self, dataset: DashAIDataset) -> DashAIDataset:
        """Convert the dataset to a format suitable for the model.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be converted.

        Returns
        -------
        Any
            The converted dataset.
        """
        raise NotImplementedError

    @abstractmethod
    def apply_model_transformations(self, dataset: DashAIDataset) -> Any:
        """Apply the needed transformations (type change, encodigns) for the model to be able to perform.

        Parameters
        ----------
        dataset : DashAIDataset
            The target dataset to be transformed.

        Returns
        -------
        Any
            The transformed target dataset.
        """
        raise NotImplementedError
