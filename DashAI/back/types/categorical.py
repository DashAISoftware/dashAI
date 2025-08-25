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
    converted : bool
        Indicates whether the categorical variable has experimented changes via converters(e.g., encoded).
    """
    
    categories: pa.Array  # List of unique category values. Maybe could be a list. I think I overcomplicated it by using pa.Array, but should't be hard to change if needed.
    converted: bool = False

    def __init__(self, values: pa.Array, encoding: dict = None, converted: bool = False):

        self.categories = values
        self.converted = converted
        
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
        # categories might contain non-string values, so convert them to strings for representation
        return {"type": "Categorical", "categories": [str(c) for c in self.categories], "num_categories": self.num_categories(), "converted": self.converted}
