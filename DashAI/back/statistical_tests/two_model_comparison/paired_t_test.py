from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class PairedTTest(BaseStatisticalTest):
    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Paired T-Test."""
        return {
            "name": "Paired T-Test",
            "is_parametric": True,
            "posthoc": False,
            "min_runs": 2,
            "description": {
                "en": """Parametric test for comparing
                two models on identical data""",
                "es": """Prueba paramétrica para comparar
                dos modelos en datos idénticos""",
                "pt": """Teste paramétrico para comparar
                dois modelos nos mesmos dados""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        alternative: str = "two-sided",
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import ttest_rel

        if len(scores) != 2:
            raise ValueError("Paired T-Test requires exactly two sets of scores.")

        run_names = list(scores.keys())
        scores1 = np.array(scores[run_names[0]])
        scores2 = np.array(scores[run_names[1]])

        if len(scores1) != len(scores2):
            raise ValueError(
                "Both sets of scores must have the same number of observations."
            )

        # Validar que haya suficientes observaciones
        if len(scores1) < 2:
            raise ValueError(
                "Paired T-Test requires at least 2 observations per group."
            )

        # Validar que no haya valores NaN
        if np.isnan(scores1).any() or np.isnan(scores2).any():
            raise ValueError("Scores contain NaN values. Please check your input data.")

        # Validar que haya varianza en los datos
        if np.var(scores1) == 0 or np.var(scores2) == 0:
            raise ValueError(
                "One or both score sets have zero variance. "
                "All values are identical, making the t-test undefined."
            )

        statistic, p_value = ttest_rel(scores1, scores2, alternative=alternative)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={
                "run_1": run_names[0],
                "run_2": run_names[1],
                "scores_run_1": scores1.tolist(),
                "scores_run_2": scores2.tolist(),
                "alternative": alternative,
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
                "alternative": {
                    "type": "string",
                    "enum": ["two-sided", "greater", "less"],
                    "default": "two-sided",
                    "description": (
                        "Alternative hypothesis. "
                        "'two-sided': the distributions differ. "
                        "'greater': the first model scores higher. "
                        "'less': the second model scores higher."
                    ),
                },
            },
        }
