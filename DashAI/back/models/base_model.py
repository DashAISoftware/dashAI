"""Base Model abstract class."""

from abc import ABCMeta, abstractmethod
from typing import Any, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract class of all machine learning models.

    All models must extend this class and implement
    save, load and prepare_dataset methods.
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
    def prepare_dataset(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        prediction : bool
            Whether the dataset is for prediction or not.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        raise NotImplementedError
