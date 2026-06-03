from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class BartlettTest(BaseStatisticalTest):
    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Bartlett's Test."""
        return {
            "name": "Bartlett's Test",
            "is_parametric": None,
            "posthoc": False,
            "min_runs": 2,
            "description": {
                "en": """Test for homogeneity of variances across groups,
                sensitive to normality""",
                "es": """Prueba de homogeneidad de varianzas entre grupos,
                sensible a la normalidad""",
                "pt": """Teste de homogeneidade de variâncias entre grupos,
                sensível à normalidade""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import bartlett

        if len(scores) < 2:
            raise ValueError("Bartlett's Test requires at least two sets of scores.")

        data = [np.array(scores[run_name]) for run_name in scores]
        statistic, p_value = bartlett(*data)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
        )
