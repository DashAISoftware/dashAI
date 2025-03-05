from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Final

from sklearn.base import BaseEstimator, TransformerMixin

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseConverter(ConfigObject, BaseEstimator, TransformerMixin, metaclass=ABCMeta):
    """Base class for all converters"""

    TYPE: Final[str] = "Converter"

    @abstractmethod
    def fit(self, dataset: DashAIDataset) -> "BaseConverter":
        """Fit the converter.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to fit the converter
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, dataset: DashAIDataset) -> DashAIDataset:
        """Transform the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to be converted

        Returns
        -------
            Dataset converted
        """
        raise NotImplementedError
