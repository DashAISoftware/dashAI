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

    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Nemenyi Test."""
        return {
            "name": "Nemenyi",
            "is_parametric": False,
            "min_runs": 3,
            "max_runs": None,
            "description": {
                "en": """Non-parametric post-hoc
                test with Nemenyi correction""",
                "es": """Prueba post-hoc no
                paramétrica con corrección de Nemenyi""",
                "pt": """Teste post-hoc não-paramétrico
                com correção de Nemenyi""",
            },
        }

    def run(
        self,
        scores: dict[str, list[float]],
        alpha: float = 0.05,
        statistic: float = None,  # Friedman statistic
        p_value: float = None,  # Friedman p-value
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
        if statistic is not None and p_value is not None:
            friedman_stat, friedman_p = statistic, p_value
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

        overall_significant = friedman_p < alpha

        return StatisticalTestResult(
            statistic=float(friedman_stat),
            p_value=float(friedman_p),
            significant=overall_significant,
            alpha=alpha,
            details={
                "runs": run_names,
                "score_arrays": [a.tolist() for a in score_arrays],
                "posthoc_matrix": posthoc_matrix.to_dict(),
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
