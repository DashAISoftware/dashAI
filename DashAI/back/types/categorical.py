from dataclasses import dataclass

import pyarrow as pa

# from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.types.dashai_data_type import DashAIDataType


@dataclass
class Categorical(DashAIDataType):
    """Represents a categorical variable.

    Attributes
    ----------
    categories : list
        List of unique category values (can be strings or numbers).
    """

    categories: pa.Array  # List of unique category values

    def __init__(self, values: pa.Array):
        """Initialize a Categorical type.

        Parameters
        ----------
        arrow_type : pa.DataType
            The PyArrow data type of the column.
        values : pa.Array
            The values in the column to extract categories.
        """

        # if not pa.types.is_dictionary(arrow_type):
        #     raise ValueError(f"Expected a dictionary (categorical) type, got {arrow_type}")

        # Extraer categorías en su tipo original
        self.categories = values

        self._str2int = {cat: idx for idx, cat in enumerate(self.categories)}
        self._int2str = {idx: cat for idx, cat in enumerate(self.categories)}

        # print(f"Categorical initialized with categories: {self.categories}")

    def str2int(self, value):
        return self._str2int[value]

    def int2str(self, value):
        return self._int2str[value]

    def num_categories(self):
        """Get the number of unique categories."""
        return len(self.categories)

    def to_string(self):
        return {
            "type": "Categorical",
            "categories": self.categories,
            "num_categories": self.num_categories(),
        }
