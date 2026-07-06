from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class PairedTTest(BaseStatisticalTest):
    """Parametric test for comparing two models on identical data."""

    DISPLAY_NAME: str = MultilingualString(
        en="Paired T-Test",
        es="Prueba T Pareada",
        pt="Teste T Pareado",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Parametric test for comparing two related groups. Requires "
            "normality of pairwise differences and independence between "
            "observations.",
        ),
        es=(
            "Prueba paramétrica para comparar dos grupos relacionados. Requiere ",
            "normalidad de las diferencias entre pares e independencia entre ",
            "observaciones.",
        ),
        pt=(
            "Teste paramétrico para comparar dois grupos relacionados. Requer ",
            "normalidade das diferenças entre pares e independência entre ",
            "observações.",
        ),
    )
    ICON: str = "CompareArrows"
    COLOR: str = "#64B5F6"

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for Paired T-Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": True,
            "posthoc": False,
            "min_runs": 2,
            "max_runs": 2,
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

        result = ttest_rel(scores1, scores2, alternative=alternative)
        statistic = result.statistic
        p_value = result.pvalue
        deg = getattr(result, "df", len(scores1) - 1)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={
                "degrees_of_freedom": deg,
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
