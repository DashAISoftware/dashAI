from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import (
    PairwiseResult,
    StatisticalTestResult,
)


class TukeyHSDTest(BaseStatisticalTest):
    """Tukey HSD post-hoc test for pairwise comparison after a significant ANOVA test.

    Controls the familywise error rate (FWER) when performing multiple pairwise
    comparisons. Assumes normality and homogeneity of variance (same assumptions
    as ANOVA). For non-normal data, use Nemenyi after Friedman instead.

    Requires the `statsmodels` package.
    """

    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Tukey HSD Test."""
        return {
            "name": "Tukey HSD",
            "is_parametric": True,
            "min_runs": 3,
            "max_runs": None,
            "description": {
                "en": """Parametric post-hoc test
                for pairwise model comparisons""",
                "es": """Prueba post-hoc
                paramétrica para comparaciones pareadas de modelos""",
                "pt": """Teste post-hoc paramétrico
                para comparações pareadas de modelos""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],
        alpha: float = 0.05,
        statistic: float = None,  # ANOVA F-statistic
        p_value: float = None,  # ANOVA p-value
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import f_oneway
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        if len(scores) < 3:
            raise ValueError(
                "Tukey HSD test requires at least three sets of scores. "
                "For pairwise comparisons use paired t-test instead."
            )

        run_names = list(scores.keys())
        score_arrays = [np.array(scores[name]) for name in run_names]

        num_observations = len(score_arrays[0])
        for arr in score_arrays:
            if len(arr) != num_observations:
                raise ValueError(
                    "All sets of scores must have the same number of observations."
                )

        # Use precalculated ANOVA values if provided, otherwise compute
        if statistic is not None and p_value is not None:
            anova_stat, anova_p = statistic, p_value
        else:
            anova_stat, anova_p = f_oneway(*score_arrays)

        # Build flat arrays for statsmodels
        all_scores = np.concatenate(score_arrays)
        all_labels = np.concatenate(
            [np.full(len(arr), name) for name, arr in zip(run_names, score_arrays)]
        )

        tukey = pairwise_tukeyhsd(all_scores, all_labels, alpha=alpha)

        # Parse pairwise results from tukey summary
        pairwise = []
        for row in tukey.summary().data[1:]:  # skip header row
            run_1, run_2, _, _, _, _, reject = row
            # p-value not directly exposed, derive significance from reject flag
            # and get adjusted p-value from meandiffs table
            p_val = float(tukey.pvalues[len(pairwise)])
            pairwise.append(
                PairwiseResult(
                    run_1=str(run_1),
                    run_2=str(run_2),
                    p_value=p_val,
                    significant=bool(reject),
                )
            )

        overall_significant = anova_p < alpha

        return StatisticalTestResult(
            statistic=float(anova_stat),
            p_value=float(anova_p),
            significant=overall_significant,
            alpha=alpha,
            details={
                "runs": run_names,
                "score_arrays": [a.tolist() for a in score_arrays],
                "tukey_summary": str(tukey.summary()),
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
