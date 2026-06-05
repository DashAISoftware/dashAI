from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class AnovaTest(BaseStatisticalTest):
    """Parametric test for comparing 3 or more models on identical data."""

    DISPLAY_NAME: str = MultilingualString(
        en="ANOVA",
        es="ANOVA",
        pt="ANOVA",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Parametric test for comparing the means of three or more groups. ",
            "Requires normality and homoscedasticity.",
        ),
        es=(
            "Prueba paramétrica para comparar las medias de tres o más grupos. ",
            "Requiere normalidad y homocedasticidad.",
        ),
        pt=(
            "Teste paramétrico para comparar as médias de três ou mais grupos. ",
            "Requer normalidade e homocedasticidade.",
        ),
    )
    ICON: str = "BarChart"
    COLOR: str = "#64B5F6"

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for ANOVA Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": True,
            "posthoc": False,
            "min_runs": 3,
            "max_runs": None,
            "supports_alternative": False,
            "interpretation": MultilingualString(
                en={
                    "significant": (
                        "There are significant differences between the models. "
                        "Post-hoc pairwise comparisons (Tukey HSD) identify which "
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
                        "Las comparaciones post-hoc (Tukey HSD) identifican qué "
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
                        "Comparações post-hoc (Tukey HSD) identificam quais "
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
