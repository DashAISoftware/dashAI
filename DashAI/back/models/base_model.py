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

    def prepare_dataset(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Hook for model-specific preprocessing.

        Override in subclasses needing
        custom tokenization/encoding. Must not mutate input in-place.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool
            Whether the dataset is for fitting or not.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        return dataset
