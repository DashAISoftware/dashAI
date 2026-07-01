"""Base Model abstract class."""

import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final

from DashAI.back.config_object import ConfigObject

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logger = logging.getLogger(__name__)


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract base class for all machine learning models in DashAI.

    All models must extend this class and implement the abstract methods
    `save`, `load`, and `train`. Evaluation is owned by task-specific
    executors or mixins, not by the universal model contract.
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
            Dictionary containing UI metadata such as the
            model icon used in the DashAI frontend.
        """
        metadata: Dict[str, Any] = {}
        metadata["icon"] = cls.ICON if cls.ICON else "Science"

        return metadata

    @abstractmethod
    def save(self, filename: str) -> None:
        """Store the model to disk.

        Parameters
        ----------
        filename : str
            Path where the model will be saved.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, filename: str) -> Any:
        """Restore a model instance from disk.

        Parameters
        ----------
        filename : str
            Path where the model was previously saved.

        Returns
        -------
        Any
            The restored model instance.
        """
        raise NotImplementedError

    @abstractmethod
    def train(
        self,
        *args,
        **kwargs,
    ) -> "BaseModel":
        """Train the model with the data required by its task executor.
        The concrete signature depends on the modeling problem.

        Returns
        -------
        BaseModel
            The trained model instance.
        """
        raise NotImplementedError

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Hook for model specific preprocessing of input features.

        Override in subclasses that require custom tokenization, encoding,
        or any other input transformation. Must not mutate the input in place.

        Parameters
        ----------
        dataset : DashAIDataset
            The input dataset to preprocess.
        is_fit : bool
            Whether the call is part of a fitting phase.
            Defaults to False.

        Returns
        -------
        DashAIDataset
            The preprocessed dataset ready to be fed into
            the model.
        """
        return dataset

    def prepare_output(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Hook for model-specific preprocessing of output targets.

        This default exists for backward compatibility with supervised models that
        preprocess targets. Unsupervised models are not required to use it.

        By default, delegates to `prepare_dataset`. Override in subclasses
        that need separate input and output preprocessing logic.

        Parameters
        ----------
        dataset : DashAIDataset
            The output dataset (target labels) to
            preprocess.
        is_fit : bool
            Whether the call is part of a fitting phase.
            Defaults to False.

        Returns
        -------
        DashAIDataset
            The preprocessed output dataset.
        """
        return self.prepare_dataset(dataset, is_fit)
