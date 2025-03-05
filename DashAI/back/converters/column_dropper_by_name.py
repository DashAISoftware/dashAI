from typing import List, Type, Union

from beartype import beartype

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ColumnDropperByName(BaseConverter):
    """Converter to drop columns from the dataset"""

    @beartype
    def __init__(self, column_names: Union[List[str], str]):
        """Constructor with columns to be dropped by column name

        Parameters
        ----------
        columns : list[str] | str
            Columns to be dropped. The list contains the names of the columns to be
            dropped. The string contains the name of the column to be dropped.
        """
        if isinstance(column_names, str):
            column_names = [column_names]
        self.column_names = column_names

    @beartype
    def fit(self, dataset: DashAIDataset) -> Type["BaseConverter"]:
        """Fit the converter.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to fit the converter
        """
        return self

    @beartype
    def transform(self, dataset: DashAIDataset) -> DashAIDataset:
        """Convert the dataset by removing columns.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to be converted

        Returns
        -------
        DatasetDict
            Dataset converted
        """
        dataset = dataset.remove_columns(self.column_names)
        return dataset
