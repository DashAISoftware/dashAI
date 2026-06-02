from abc import ABCMeta, abstractmethod

from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class BaseStatisticalTest(metaclass=ABCMeta):
    TYPE = "StatisticalTest"

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

    def get_metadata(self) -> dict:
        """
        Returns metadata about the statistical test.
        Subclasses can override this method to customize metadata.

        Default metadata:
        - is_parametric: Whether the test is parametric
        - min_runs: Minimum number of runs required
        - max_runs: Maximum number of runs (None = unlimited)
        - description: Brief description in multiple languages
        """
        return {
            "is_parametric": False,  # Override in subclasses
            "min_runs": 2,
            "max_runs": None,
            "description": {
                "en": "Statistical test",
                "es": "Prueba estadística",
                "pt": "Teste estatístico",
            },
        }
