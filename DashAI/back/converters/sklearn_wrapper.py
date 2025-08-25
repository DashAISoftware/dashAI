from abc import ABCMeta
from typing import Type, Union

import numpy as np
import pandas as pd

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
    dashai_to_pandas,
)

from DashAI.back.converters.converter_types import SKLEARN_CONVERTERS_TYPES

from DashAI.back.types.categorical import Categorical
import pyarrow as pa

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

    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> Type[BaseConverter]:
        """Generic fit method for sklearn transformers"""

        x_pandas = dashai_to_pandas(x)
        if y is not None:
            y_pandas = dashai_to_pandas(y)

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

        x_pandas = dashai_to_pandas(x)
        x_new = super(BaseConverter, self).transform(x_pandas)

        if isinstance(x_new, np.ndarray):
            columns = x_pandas.columns if hasattr(x_pandas, "columns") else None
            x_new = pd.DataFrame(x_new, columns=columns)

        converted_dataset = to_dashai_dataset(x_new)

        converter_name = self.__class__.__name__
        dashai_type = SKLEARN_CONVERTERS_TYPES.get(converter_name, None)

        for col in converted_dataset.column_names:
            if dashai_type is not None:
                #Exclusive for categorical values, since it's not that easy to initialize them.
                if isinstance(dashai_type, Categorical):
                    if hasattr(self, "classes_"):
                        values = pa.array(self.classes_.tolist())
                        encoding = {v: i for i, v in enumerate(self.classes_)}
                        converted_dataset.types[col] = Categorical(values=values, encoding=encoding, converted=True)

                else:
                    converted_dataset.types[col] = dashai_type
            else:
                print("Converter type not found for", converter_name, ". This could be on purpose depending on the converter used. Check the dictionary in converter_types.py")

        return converted_dataset
