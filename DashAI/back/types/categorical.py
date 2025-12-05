from dataclasses import dataclass
from typing import Union

import pyarrow as pa

from DashAI.back.types.dashai_data_type import DashAIDataType


@dataclass
class Categorical(DashAIDataType):
    """Represents a categorical variable.

    Attributes
    ----------
    categories : pa.Array
        Array of unique category values (can be strings or numbers).
    converted : bool
        Indicates whether the categorical variable has
        experimented changes via converters(e.g., encoded).
    """

    # Array of unique category values. Maybe could be a list.
    # I think I overcomplicated it by using pa.Array
    # But should't be hard to change if needed.
    categories: pa.Array
    converted: bool = False
    dtype: str = None

    def __init__(
        self,
        values: Union[pa.Array, list],
        encoding: dict = None,
        converted: bool = False,
        dtype: str = None,
    ):
        # Convert list to pa.Array if needed
        if isinstance(values, list):
            values = pa.array(values)

        self.categories = values
        self.converted = converted

        # Infer dtype from values if not explicitly provided
        if dtype is None:
            self.dtype = self._infer_dtype(values)
        else:
            self.dtype = dtype

        if encoding is not None:
            sample_key = next(iter(encoding))
            sample_value = encoding[sample_key]
            if isinstance(sample_value, str):
                # If the encoding is a string mapping, convert it to a dictionary
                self._str2int = {v: k for k, v in encoding.items()}
                self._int2str = encoding
            elif isinstance(sample_value, int):
                self._str2int = encoding
                self._int2str = {v: k for k, v in encoding.items()}
        else:
            self._str2int = {cat: idx for idx, cat in enumerate(self.categories)}  # noqa: C416
            self._int2str = {idx: cat for idx, cat in enumerate(self.categories)}  # noqa: C416

    def str2int(self, value):
        return self._str2int[value]

    def int2str(self, value):
        return self._int2str[value]

    def _infer_dtype(self, values: pa.Array) -> str:
        """Infer the dtype from the values array.

        Parameters
        ----------
        values : pa.Array
            Array of category values.

        Returns
        -------
        str
            The inferred dtype: 'int64', 'float64', or 'string'.
        """
        if len(values) == 0:
            return "string"

        # Check the PyArrow type
        arrow_type = values.type

        # Map PyArrow types to string representations
        if pa.types.is_integer(arrow_type):
            return "int64"
        elif pa.types.is_floating(arrow_type):
            return "float64"
        elif pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            return "string"
        else:
            # For other types, try to infer from the first non-null value
            for val in values:
                if val.is_valid:
                    py_val = val.as_py()
                    if isinstance(py_val, int):
                        return "int64"
                    elif isinstance(py_val, float):
                        return "float64"
                    else:
                        return "string"
            return "string"

    def num_categories(self):
        """Get the number of unique categories."""
        return len(self.categories)

    def to_string(self):
        # categories might contain non-string values,
        # so convert them to strings for representation
        return {
            "type": "Categorical",
            "dtype": self.dtype,
            "categories": [str(c) for c in self.categories],
            "num_categories": self.num_categories(),
            "converted": self.converted,
        }
