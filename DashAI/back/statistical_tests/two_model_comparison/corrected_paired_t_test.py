from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class CorrectedPairedTTest(BaseStatisticalTest):
    """Corrected Paired t-test for comparing two models evaluated with cross-validation.

    Based on Nadeau & Bengio (2003), this test corrects the standard paired t-test
    to account for the fact that CV folds are not independent, sharing training data.
    The standard paired t-test underestimates variance in this setting, leading to
    inflated Type I error rates. The correction factor is:

        var_corrected = (1/k + n_test/n_train) * var_differences

    where k is the number of folds, n_test is the test set size per fold, and
    n_train is the training set size per fold.

    References
    ----------
    Nadeau, C., & Bengio, Y. (2003). Inference for the Generalization Error.
    Machine Learning, 52(3), 239-281.
    """

    @staticmethod
    def get_metadata() -> dict:
        """Metadata for Corrected Paired T-Test."""
        return {
            "name": "Corrected Paired t-test",
            "is_parametric": True,
            "posthoc": False,
            "min_runs": 2,
            "max_runs": 2,
            "description": {
                "en": """Paired t-test with correction
                for cross-validation dependencies""",
                "es": """Prueba t pareada con
                corrección para dependencias de validación cruzada""",
                "pt": """Teste t pareado com correção
                para dependências de validação cruzada""",
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
        from scipy import stats

        if len(scores) != 2:
            raise ValueError(
                "Corrected Paired t-test requires exactly two sets of scores."
            )

        run_names = list(scores.keys())
        scores1 = np.array(scores[run_names[0]])
        scores2 = np.array(scores[run_names[1]])

        if len(scores1) != len(scores2):
            raise ValueError(
                "Both sets of scores must have the same number of observations."
            )

        k = len(scores1)  # number of folds

        # Ratio used in the correction factor.
        # For standard k-fold CV: n_test/n_train = (1/k) / (1 - 1/k) = 1/(k-1)
        # This is the standard approximation when dataset size is not available.
        correction_factor = 1 / k + 1 / (k - 1)

        differences = scores1 - scores2
        mean_diff = np.mean(differences)
        var_diff = np.var(differences, ddof=1)

        # Apply Nadeau & Bengio correction to the variance
        corrected_var = correction_factor * var_diff
        corrected_std = np.sqrt(corrected_var)

        if corrected_std == 0:
            raise ValueError(
                "Corrected standard deviation is zero — "
                "all fold differences are identical."
            )

        # t-statistic with corrected variance
        t_statistic = mean_diff / corrected_std
        # Two-tailed p-value with k-1 degrees of freedom
        if alternative == "two-sided":
            p_value = 2 * stats.t.sf(np.abs(t_statistic), df=k - 1)
        elif alternative == "greater":
            p_value = stats.t.sf(t_statistic, df=k - 1)
        else:  # less
            p_value = stats.t.cdf(t_statistic, df=k - 1)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(t_statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={
                "run_1": run_names[0],
                "run_2": run_names[1],
                "scores_run_1": scores1.tolist(),
                "scores_run_2": scores2.tolist(),
                "differences": differences.tolist(),
                "mean_difference": float(mean_diff),
                "n_folds": k,
                "correction_factor": float(correction_factor),
                "corrected_variance": float(corrected_var),
                "degrees_of_freedom": k - 1,
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
