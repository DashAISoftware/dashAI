from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class FriedmanTest(BaseStatisticalTest):
    """Non-parametric alternative to ANOVA for comparing 3+ models."""

    DISPLAY_NAME: str = MultilingualString(
        en="Friedman Test",
        es="Prueba de Friedman",
        pt="Teste de Friedman",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Non-parametric test for comparing multiple models on the same folds. ",
            "Does not assume normality.",
        ),
        es=(
            "Prueba no paramétrica para comparar múltiples modelos sobre ",
            "los mismos folds. No asume normalidad.",
        ),
        pt=(
            "Teste não-paramétrico para comparar múltiplos modelos sobre ",
            "as mesmas folds. Não assume normalidade.",
        ),
    )
    ICON: str = "Leaderboard"
    COLOR: str = "#FFD54F"
    COMPATIBLE_COMPONENTS = ["NemenyiTest"]

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for Friedman Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": False,
            "is_posthoc": False,
            "min_runs": 3,
            "max_runs": None,
            "supports_alternative": False,
            "supports_correction": False,
            "interpretation": MultilingualString(
                en={
                    "significant": (
                        "There are significant differences between the models. "
                        "Post-hoc pairwise comparisons (Nemenyi) identify which "
                        "pairs differ."
                    ),
                    "not_significant": (
                        "No significant differences between the models. "
                        "They perform similarly."
                    ),
                },
                es={
                    "significant": (
                        "Hay diferencias significativas entre los modelos. "
                        "Las comparaciones post-hoc (Nemenyi) identifican qué "
                        "pares difieren."
                    ),
                    "not_significant": (
                        "No hay diferencias significativas entre los modelos. "
                        "Tienen un rendimiento similar."
                    ),
                },
                pt={
                    "significant": (
                        "Há diferenças significativas entre os modelos. "
                        "Comparações post-hoc (Nemenyi) identificam quais "
                        "pares diferem."
                    ),
                    "not_significant": (
                        "Não há diferenças significativas entre os modelos. "
                        "Eles têm desempenho similar."
                    ),
                },
            ),
        }

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import friedmanchisquare

        if len(scores) < 3:
            raise ValueError("Friedman Test requires at least three sets of scores.")

        run_names = list(scores.keys())
        score_arrays = [np.array(scores[run_name]) for run_name in run_names]

        # Check that all score arrays have the same number of observations
        num_observations = len(score_arrays[0])
        for arr in score_arrays:
            if len(arr) != num_observations:
                raise ValueError(
                    "All sets of scores must have the same number of observations."
                )

        statistic, p_value = friedmanchisquare(*score_arrays)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={},
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
