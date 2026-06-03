from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class WilcoxonSRTest(BaseStatisticalTest):
    """Non-parametric alternative to paired t-test for two models."""

    DISPLAY_NAME: str = MultilingualString(
        en="Wilcoxon Signed-Rank",
        es="Wilcoxon Rango con Signo",
        pt="Wilcoxon Posto com Sinal",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Non-parametric test for comparing two related groups. ",
            "Requires paired observations and does not assume normality.",
        ),
        es=(
            "Prueba no paramétrica para comparar dos grupos relacionados. "
            "Requiere observaciones emparejadas y no asume normalidad."
        ),
        pt=(
            "Alternativa não-paramétrica ao teste t pareado para dois modelos. "
            "Requer observações emparejadas e não assume normalidade."
        ),
    )
    ICON: str = "CompareArrows"
    COLOR: str = "#FFD54F"

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for Wilcoxon Signed-Rank Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": False,
            "posthoc": False,
            "min_runs": 2,
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        alternative: str = "two-sided",
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import wilcoxon

        if len(scores) != 2:
            raise ValueError(
                "Wilcoxon Signed-Rank Test requires exactly two sets of scores."
            )

        run_names = list(scores.keys())
        scores1 = np.array(scores[run_names[0]])
        scores2 = np.array(scores[run_names[1]])

        if len(scores1) != len(scores2):
            raise ValueError(
                "Both sets of scores must have the same number of observations."
            )

        # we round the scores to 4 decimal places to avoid issues
        # with very small differences, according to scipy documentation
        score_differences = np.round(scores1 - scores2, decimals=4)
        statistic, p_value = wilcoxon(score_differences, alternative=alternative)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=statistic,
            p_value=p_value,
            significant=significant,
            alpha=alpha,
            details={
                "run_1": run_names[0],
                "run_2": run_names[1],
                "scores_run_1": scores1.tolist(),
                "scores_run_2": scores2.tolist(),
                "score_differences": score_differences.tolist(),
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
                        "Alternative hypothesis."
                        "'two-sided': the distributions differ. "
                        "'greater': the first model scores higher. "
                        "'less': the second model scores higher."
                    ),
                },
            },
        }
