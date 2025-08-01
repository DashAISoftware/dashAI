from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Final, Type, Union

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseConverter(ConfigObject, metaclass=ABCMeta):
    """
    Base class for all converters

    Converters are for modifying the data in a supervised or unsupervised way
    (e.g. by adding, changing, or removing columns, but not by adding or removing rows)
    """

    TYPE: Final[str] = "Converter"

    def changes_row_count(self) -> bool:
        """
        Indicates if the converter changes the number of rows in the dataset.
        Samplers typically do, while most other transformers do not.
        """
        return False

    @abstractmethod
    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> Type[BaseConverter]:
        """Fit the converter.
        This method should allow to validate the converter's parameters.

        Parameters
        ----------
        X : DashAIDataset
            Training data
        y: DashAIDataset
            Target data for supervised learning

        Returns
        ----------
        self
            The fitted converter object.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """Transform the dataset.

        Parameters
        ----------
        X : DashAIDataset
            Dataset to be converted
        y: DashAIDataset
            Target vectors

        Returns
        -------
            Dataset converted
        """
        raise NotImplementedError
