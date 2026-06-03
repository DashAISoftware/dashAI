from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class LeveneTest(BaseStatisticalTest):
    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Levene's Test."""
        return {
            "name": "Levene's Test",
            "is_parametric": None,
            "posthoc": False,
            "min_runs": 2,
            "description": {
                "en": """Test for homogeneity of variances
                across groups""",
                "es": """Prueba de homogeneidad de varianzas
                entre grupos""",
                "pt": """Teste de homogeneidade de variâncias
                entre grupos""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import levene

        if len(scores) < 2:
            raise ValueError("Levene's Test requires at least two sets of scores.")

        data = [np.array(scores[run_name]) for run_name in scores]
        statistic, p_value = levene(*data)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
        )
