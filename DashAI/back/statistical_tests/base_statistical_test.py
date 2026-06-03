from abc import ABCMeta, abstractmethod
from typing import Any, Dict

from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class BaseStatisticalTest(metaclass=ABCMeta):
    TYPE = "StatisticalTest"
    ICON: str = "Science"

    @abstractmethod
    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_schema(self) -> dict:
        # Para que el frontend pueda renderizar
        # la configuración (alpha, etc.) dinámicamente
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    @abstractmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current test.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing UI metadata
        """
        raise NotImplementedError("Subclasses must implement this method")
