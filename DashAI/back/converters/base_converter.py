from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Final, Type

import pandas as pd

from DashAI.back.config_object import ConfigObject


class BaseConverter(ConfigObject, metaclass=ABCMeta):
    """
    Base class for all converters

    Converters are for modifying the data in a supervised or unsupervised way
    (e.g. by adding, changing, or removing columns, but not by adding or removing rows)
    """

    TYPE: Final[str] = "Converter"

    @abstractmethod
    def fit(self, x: pd.DataFrame, y: pd.Series = None) -> Type[BaseConverter]:
        """Fit the converter.
        This method should allow to validate the converter's parameters.

        Parameters
        ----------
        X : Pandas DataFrame
            Training data
        y: Pandas Series
            Target data for supervised learning

        Returns
        ----------
        self
            The fitted converter object.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, x: pd.DataFrame, y: pd.Series = None) -> pd.DataFrame:
        """Transform the dataset.

        Parameters
        ----------
        X : Pandas DataFrame
            Dataset to be converted
        y: Pandas Series
            Target vectors

        Returns
        -------
            Dataset converted
        """
        raise NotImplementedError
