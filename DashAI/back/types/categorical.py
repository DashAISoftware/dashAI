from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from DashAI.back.types.dashai_data_type import DashAIDataType

if TYPE_CHECKING:
    from pyarrow import Array


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

    categories: list
    converted: bool = False
    dtype: str = None

    def __init__(
        self,
        values: Union["Array", list],
        encoding: dict = None,
        converted: bool = False,
        dtype: str = None,
    ):
        import pyarrow as pa

        # Convert pa.Array to list if needed
        if isinstance(values, pa.Array):
            values = values.to_pylist()

        if isinstance(values, list) and dtype:
            if dtype == "bool":

                def to_bool(v):
                    if v is None:
                        return None
                    if isinstance(v, str):
                        return v == "True"
                    return bool(v)

                values = [to_bool(v) for v in values]
            elif dtype.startswith("int"):
                values = [int(v) if v is not None else None for v in values]
            elif dtype.startswith("float"):
                values = [float(v) if v is not None else None for v in values]

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
            enum_dict = dict(enumerate(self.categories))
            self._int2str = enum_dict
            self._str2int = {v: k for k, v in enum_dict.items()}

    def str2int(self, value):
        return self._str2int[value]

    def int2str(self, value):
        return self._int2str[value]

    def _infer_dtype(self, values: list) -> str:
        """Infer the dtype from the values list.

        Parameters
        ----------
        values : list
            List of category values.

        Returns
        -------
        str
            The inferred dtype: 'int64', 'float64', 'bool', or 'string'.
        """
        if len(values) == 0:
            return "string"

        # Check the type of the first non-None value
        for val in values:
            if val is not None:
                if isinstance(val, bool):
                    return "bool"
                elif isinstance(val, int):
                    return "int64"
                elif isinstance(val, float):
                    return "float64"
                else:
                    return "string"

        return "string"

    def num_categories(self):
        """Get the number of unique categories."""
        return len(self.categories)

    def to_string(self):
        # categories might contain non-string values
        return {
            "type": "Categorical",
            "dtype": self.dtype,
            "categories": [str(c) for c in self.categories],
            "num_categories": self.num_categories(),
            "converted": self.converted,
        }
