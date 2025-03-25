from abc import ABCMeta
from typing import Type

import pandas as pd

from DashAI.back.converters.base_converter import BaseConverter


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

    def fit(self, x: pd.DataFrame, y: pd.Series = None) -> Type[BaseConverter]:
        """Generic fit method for sklearn transformers"""

        requires_y = hasattr(self, "_get_tags") and self._get_tags().get(
            "requires_y", False
        )

        # Check for supervised transformers that require y
        if requires_y and y is None:
            raise ValueError("This transformer requires y for fitting")

        if requires_y:
            super(BaseConverter, self).fit(x, y)
        else:
            super(BaseConverter, self).fit(x)

        return self

    def transform(self, x: pd.DataFrame, y: pd.Series = None) -> pd.DataFrame:
        """Generic transform method for sklearn transformers"""

        x_new = super(BaseConverter, self).transform(x)
        return x_new
