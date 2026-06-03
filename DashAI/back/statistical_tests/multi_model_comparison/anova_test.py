from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class AnovaTest(BaseStatisticalTest):
    @staticmethod
    def get_metadata() -> dict:
        """Metadata for ANOVA Test."""
        return {
            "name": "ANOVA",
            "is_parametric": True,
            "posthoc": False,
            "min_runs": 3,
            "max_runs": None,
            "description": {
                "en": """Parametric test for comparing 3 or more models on
                identical data""",
                "es": """Prueba paramétrica para comparar 3 o más modelos en
                datos idénticos""",
                "pt": """Teste paramétrico para comparar 3 ou mais modelos nos
                mesmos dados""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import f_oneway

        if len(scores) < 3:
            raise ValueError(
                "ANOVA Test requires at least three sets of scores. "
                "For comparing two models use Paired t-test instead."
            )

        run_names = list(scores.keys())
        score_arrays = [np.array(scores[run_name]) for run_name in run_names]

        # Check that all score arrays have the same number of observations
        num_observations = len(score_arrays[0])
        for arr in score_arrays:
            if len(arr) != num_observations:
                raise ValueError(
                    "All sets of scores must have the same number of observations."
                )

        statistic, p_value = f_oneway(*score_arrays)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={
                "runs": run_names,
                "score_arrays": [a.tolist() for a in score_arrays],
            },
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "alpha": {
                    "type": "number",
                    "default": 0.05,
                    "minimum": 0.001,
                    "maximum": 0.2,
                    "description": "Significance level for the hypothesis test.",
                },
            },
        }
