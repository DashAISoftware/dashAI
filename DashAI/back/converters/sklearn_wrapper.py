from abc import ABCMeta, abstractmethod
from typing import Type, Union

import numpy as np
import pandas as pd
import pyarrow as pa

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType


class SklearnWrapper(BaseConverter, metaclass=ABCMeta):
    """Abstract class to define generic rules for sklearn transformers"""

    def __init__(self, **kwargs):
        # Initialize sklearn operation with provided parameters
        super(SklearnWrapper, self).__init__()  # Initialize BaseConverter
        super(BaseConverter, self).__init__(**kwargs)  # Initialize sklearn operation

        if hasattr(
            self, "set_output"
        ):  # Not all scikit-learn transformers support the set_output API
            self.set_output(
                transform="pandas"
            )  # Cast the output from numpy ndarray to pandas DataFrame

    @abstractmethod
    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """
        Each sklearn converter must implement this method to specify its output type.
        """
        raise NotImplementedError

    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> Type[BaseConverter]:
        """Generic fit method for sklearn transformers"""

        x_pandas = x.to_pandas()
        if y is not None:
            y_pandas = y.to_pandas()

        requires_y = hasattr(self, "_get_tags") and self._get_tags().get(
            "requires_y", False
        )

        # Check for supervised transformers that require y
        if requires_y and y is None:
            raise ValueError("This transformer requires y for fitting")

        if requires_y:
            super(BaseConverter, self).fit(x_pandas, y_pandas)
        else:
            super(BaseConverter, self).fit(x_pandas)

        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """Generic transform method for sklearn transformers"""

        x_pandas = x.to_pandas()
        x_new = super(BaseConverter, self).transform(x_pandas)

        if isinstance(x_new, np.ndarray):
            columns = x_pandas.columns if hasattr(x_pandas, "columns") else None
            x_new = pd.DataFrame(x_new, columns=columns)

        converted_dataset = to_dashai_dataset(x_new)

        for col in converted_dataset.column_names:
            try:
                output_type = self.get_output_type(col)

                # Special handling for categorical types that need class information
                if isinstance(output_type, Categorical) and hasattr(self, "classes_"):
                    values = pa.array(self.classes_.tolist())
                    encoding = {v: i for i, v in enumerate(self.classes_)}
                    converted_dataset.types[col] = Categorical(
                        values=values, encoding=encoding, converted=True
                    )
                else:
                    converted_dataset.types[col] = output_type
            except NotImplementedError:
                print(
                    f"Warning: Converter {self.__class__.__name__} does not implement "
                    f"get_output_type. Column {col} type may not be properly set."
                )

        return converted_dataset
