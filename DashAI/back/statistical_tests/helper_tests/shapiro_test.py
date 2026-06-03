from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class ShapiroTest(BaseStatisticalTest):
    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Shapiro-Wilk Test."""
        return {
            "name": "Shapiro-Wilk",
            "is_parametric": None,
            "posthoc": False,
            "min_runs": 1,
            "description": {
                "en": """Test for normality of a single set of scores""",
                "es": """Prueba de normalidad para un solo
                conjunto de puntuaciones""",
                "pt": """Teste de normalidade para um único
                conjunto de pontuações""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import shapiro

        if len(scores) != 1:
            raise ValueError("Shapiro-Wilk Test requires exactly one set of scores.")

        run_name = list(scores.keys())[0]
        data = np.array(scores[run_name])

        statistic, p_value = shapiro(data)
        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=statistic,
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
        )
