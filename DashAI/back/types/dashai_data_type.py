import pyarrow as pa
from abc import ABC, abstractmethod

class DashAIDataType(ABC):
    """Abstract base class for DashAI data types."""
    
    # @classmethod
    # @abstractmethod
    # def from_arrow(self, arrow_table: pa.Table) -> 'DashAIDataType':
    #     """Convert from Arrow table to DashAI data type."""
    #     pass

    @abstractmethod
    def transform(self, arrow_column: pa.Array, target_library: str) -> pa.Array:
        """Transform column to the specified library format."""
        pass

    @abstractmethod
    def to_string(self) -> str:
        """Convert to string representation."""
        pass