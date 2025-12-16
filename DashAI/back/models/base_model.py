"""Base Model abstract class."""

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract class of all machine learning models.

    All models must extend this class and implement save and load methods.
    """

    TYPE: Final[str] = "Model"
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    COLOR: str = "#795548"
    ICON: str = "Science"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current model.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata including icon.
        """
        metadata: Dict[str, Any] = {}
        metadata["icon"] = cls.ICON if cls.ICON else "Science"

        return metadata

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
        """Hook for model-specific preprocessing of input features.

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

    def prepare_output(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Hook for model-specific preprocessing of output targets.

        Parameters
        ----------
        dataset : DashAIDataset
            The output dataset to be transformed.
        is_fit : bool
            Whether the dataset is for fitting or not.

        Returns
        -------
        DashAIDataset
            The prepared output dataset.
        """
        return self.prepare_dataset(dataset, is_fit)
