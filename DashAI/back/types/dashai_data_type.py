from abc import ABC, abstractmethod


class DashAIDataType(ABC):
    """Abstract base class for DashAI data types."""

    @abstractmethod
    def to_string(self) -> str:
        """Convert to string representation."""
