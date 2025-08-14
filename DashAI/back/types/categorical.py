from dataclasses import dataclass
import pyarrow as pa
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
    
    def __init__(self, values: pa.Array, encoding: dict = None):
        self.categories = values

        if encoding is not None:
            self._str2int = encoding
            self._int2str = {v: k for k, v in encoding.items()}
        else:
            self._str2int = {cat: idx for idx, cat in enumerate(self.categories)}
            self._int2str = {idx: cat for idx, cat in enumerate(self.categories)}

    def str2int(self, value):
        return self._str2int[value]
    
    def int2str(self, value):
        return self._int2str[value]
    
    def num_categories(self):
        """Get the number of unique categories."""
        return len(self.categories)

    def to_string(self):
        return {"type": "Categorical", "categories": self.categories, "num_categories": self.num_categories()}
