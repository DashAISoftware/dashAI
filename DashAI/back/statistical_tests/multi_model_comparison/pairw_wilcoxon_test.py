from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import (
    PairwiseResult,
    StatisticalTestResult,
)


class PairwiseWilcoxonTest(BaseStatisticalTest):
    """Pairwise Wilcoxon signed-rank test with Holm correction for multiple comparisons.

    Runs Wilcoxon signed-rank test for all pairs of models and applies the
    Holm-Bonferroni correction to control the familywise error rate (FWER).

    More powerful than Nemenyi because it uses actual score differences rather
    than rankings, but requires at least 3 models. For comparing exactly 2 models,
    use WilcoxonSRTest instead.

    Requires the `scikit-posthocs` package.

    References
    ----------
    Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure.
    Scandinavian Journal of Statistics, 6(2), 65-70.
    """

    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Pairwise Wilcoxon Test."""
        return {
            "name": "Pairwise Wilcoxon",
            "is_parametric": False,
            "posthoc": False,
            "min_runs": 3,
            "max_runs": None,
            "description": {
                "en": """Post-hoc non-parametric pairwise
                comparisons after Friedman test""",
                "es": """Comparaciones pareadas
                no paramétricas post-hoc después de la prueba de Friedman""",
                "pt": """Comparações pareadas
                não-paramétricas post-hoc após teste de Friedman""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        import scikit_posthocs as sp

        if len(scores) < 3:
            raise ValueError(
                "Pairwise Wilcoxon test requires at least three sets of scores. "
                "For comparing exactly two models use WilcoxonSRTest instead."
            )

        run_names = list(scores.keys())
        score_arrays = [np.array(scores[name]) for name in run_names]

        num_observations = len(score_arrays[0])
        for arr in score_arrays:
            if len(arr) != num_observations:
                raise ValueError(
                    "All sets of scores must have the same number of observations."
                )

        data_matrix = np.array(score_arrays)

        # posthoc_wilcoxon applies Holm correction by default (p_adjust="holm")
        posthoc_matrix = sp.posthoc_wilcoxon(
            data_matrix,
            p_adjust="holm",
        )

        # Build pairwise results from the upper triangle of the matrix
        pairwise = []
        for i in range(len(run_names)):
            for j in range(i + 1, len(run_names)):
                p_val = float(posthoc_matrix.iloc[i, j])
                pairwise.append(
                    PairwiseResult(
                        run_1=run_names[i],
                        run_2=run_names[j],
                        p_value=p_val,
                        significant=p_val < alpha,
                    )
                )

        significant_pairs = [p for p in pairwise if p.significant]
        overall_significant = len(significant_pairs) > 0

        return StatisticalTestResult(
            statistic=float("nan"),  # no single omnibus statistic
            p_value=float("nan"),
            significant=overall_significant,
            alpha=alpha,
            details={
                "runs": run_names,
                "score_arrays": [a.tolist() for a in score_arrays],
                "posthoc_matrix": posthoc_matrix.to_dict(),
                "p_adjust": "holm",
            },
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
            },
        }
