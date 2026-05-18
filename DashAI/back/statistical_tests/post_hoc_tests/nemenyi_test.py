from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import (
    PairwiseResult,
    StatisticalTestResult,
)


class NemenyiTest(BaseStatisticalTest):
    """Nemenyi post-hoc test for pairwise comparison after a significant Friedman test.

    Uses rank-based pairwise comparisons with a critical difference threshold.
    Recommended by Demsar (2006) as the standard post-hoc test for comparing
    multiple classifiers evaluated with cross-validation.

    Requires the `scikit-posthocs` package.

    References
    ----------
    Demsar, J. (2006). Statistical Comparisons of Classifiers over Multiple
    Data Sets. Journal of Machine Learning Research, 7, 1-30.
    """

    def run(
        self,
        scores: dict[str, list[float]],
        alpha: float = 0.05,
        friedman_statistic: float = None,
        friedman_p_value: float = None,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        import scikit_posthocs as sp
        from scipy.stats import friedmanchisquare

        if len(scores) < 3:
            raise ValueError(
                "Nemenyi post-hoc test requires at least three sets of scores. "
                "For pairwise comparisons use Wilcoxon or Paired t-test instead."
            )

        run_names = list(scores.keys())
        score_arrays = [np.array(scores[name]) for name in run_names]

        num_observations = len(score_arrays[0])
        for arr in score_arrays:
            if len(arr) != num_observations:
                raise ValueError(
                    "All sets of scores must have the same number of observations."
                )

        # Use precalculated Friedman values if provided, otherwise compute
        if friedman_statistic is not None and friedman_p_value is not None:
            friedman_stat, friedman_p = friedman_statistic, friedman_p_value
        else:
            friedman_stat, friedman_p = friedmanchisquare(*score_arrays)

        # Build data matrix for scikit-posthocs: shape (n_folds, n_models)
        data_matrix = np.column_stack(score_arrays)
        posthoc_matrix = sp.posthoc_nemenyi_friedman(data_matrix)

        # Build pairwise results from the matrix
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
        overall_significant = friedman_p < alpha

        if not overall_significant:
            interpretation = (
                f"The Friedman test was not significant (p={friedman_p:.4f}), "
                f"so post-hoc comparisons should be interpreted with caution."
            )
        elif not significant_pairs:
            interpretation = (
                f"The Friedman test was significant (p={friedman_p:.4f}), "
                f"but no individual pairs were significantly different at "
                f"alpha={alpha}."
            )
        else:
            pair_strs = ", ".join(
                f"{p.run_1} vs {p.run_2} (p={p.p_value:.4f})" for p in significant_pairs
            )
            interpretation = (
                f"The Friedman test was significant (p={friedman_p:.4f}). "
                f"The following pairs differ significantly: {pair_strs}."
            )

        return StatisticalTestResult(
            test_name="Nemenyi Post-hoc Test",
            statistic=float(friedman_stat),
            p_value=float(friedman_p),
            significant=overall_significant,
            alpha=alpha,
            details={
                "runs": run_names,
                "score_arrays": [a.tolist() for a in score_arrays],
                "posthoc_matrix": posthoc_matrix.to_dict(),
            },
            interpretation=interpretation,
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
