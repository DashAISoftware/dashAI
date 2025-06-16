from abc import ABC, abstractmethod
from typing import Dict, Any



class InferenceMethod(ABC):
    """
    Abstract base class for inference methods.
    """

    @abstractmethod
    def infer_types(self, data) -> Dict[str, Any]:
        """
        Abstract method to infer types from the provided data.
        """
        pass


