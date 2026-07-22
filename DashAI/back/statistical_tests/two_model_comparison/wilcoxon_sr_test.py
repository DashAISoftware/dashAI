from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import (
    PairwiseResult,
    StatisticalTestResult,
)
from DashAI.back.statistical_tests.utils import CorrectionMethod, correct_p_values


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
            "max_runs": None,
            "supports_alternative": True,
            "interpretation": MultilingualString(
                en={
                    "significant": (
                        "There is a significant difference between the two models. "
                        "The results are statistically significantly different."
                    ),
                    "not_significant": (
                        "No significant difference between the two models. "
                        "They perform similarly."
                    ),
                },
                es={
                    "significant": (
                        "Hay una diferencia significativa entre los dos modelos. "
                        "Los resultados son estadísticamente significativamente "
                        "diferentes."
                    ),
                    "not_significant": (
                        "No hay diferencia significativa entre los dos modelos. "
                        "Tienen un rendimiento similar."
                    ),
                },
                pt={
                    "significant": (
                        "Há uma diferença significativa entre os dois modelos. "
                        "Os resultados são estatisticamente significativamente "
                        "diferentes."
                    ),
                    "not_significant": (
                        "Não há diferença significativa entre os dois modelos. "
                        "Eles têm desempenho similar."
                    ),
                },
            ),
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        alternative: str = "two-sided",
        correction_method: str = "holm",
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import wilcoxon

        if len(scores) < 2:
            raise ValueError(
                "Wilcoxon Signed-Rank Test requires at least two sets of scores."
            )

        run_names = list(scores.keys())

        # simple case: exactly two models, no correction needed
        if len(scores) == 2:
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
                    "score_differences": score_differences.tolist(),
                    "alternative": alternative,
                },
            )

        # more than two models: perform pairwise comparisons with correction
        preliminary_results = []
        pre_correction_p_values = []
        for i in range(len(run_names)):
            for j in range(i + 1, len(run_names)):
                scores1 = np.array(scores[run_names[i]])
                scores2 = np.array(scores[run_names[j]])

                score_differences = np.round(scores1 - scores2, decimals=4)
                statistic, p_value = wilcoxon(score_differences)

                preliminary_results.append((run_names[i], run_names[j], statistic))
                pre_correction_p_values.append(p_value)

        # Apply correction to the p-values
        corrected_p_values = correct_p_values(
            p_values=pre_correction_p_values,
            method=CorrectionMethod[correction_method.upper()],
            alpha=alpha,
        )

        results = [
            (a, b, stat, p)
            for (a, b, stat), p in zip(preliminary_results, corrected_p_values)
        ]

        overall_significant = any(p < alpha for _, _, _, p in results)
        pairwise = []

        for a, b, stat, p in results:
            pairwise.append(
                PairwiseResult(
                    run_1=a,
                    run_2=b,
                    statistic=stat,
                    p_value=p,
                    significant=p < alpha,
                )
            )

        return StatisticalTestResult(
            statistic=float("nan"),  # no single omnibus statistic
            p_value=float("nan"),
            significant=overall_significant,
            alpha=alpha,
            details={},
            posthoc=pairwise,
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
