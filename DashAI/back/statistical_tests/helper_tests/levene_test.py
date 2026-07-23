from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class LeveneTest(BaseStatisticalTest):
    """Test for homogeneity of variances across groups."""

    DISPLAY_NAME: str = MultilingualString(
        en="Levene's Test",
        es="Prueba de Levene",
        pt="Teste de Levene",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Test of homogeneity of variances between groups (homoscedasticity), "
            "robust to deviations from normality."
        ),
        es=(
            "Prueba de homogeneidad de varianzas entre grupos (homocedasticidad), "
            "robusta ante desviaciones de la normalidad."
        ),
        pt=(
            "Teste de homogeneidade de variâncias entre grupos (homocedasticidade), "
            "robusto contra desvios da normalidade."
        ),
    )
    ICON: str = "Balance"
    COLOR: str = "#4CAF50"

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for Levene's Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": None,
            "is_posthoc": False,
            "min_runs": 2,
            "max_runs": None,
            "supports_alternative": False,
            "supports_correction": False,
            "interpretation": MultilingualString(
                en={
                    "significant": (
                        "No homogeneity of variances detected. "
                        "The samples have different variances (heteroscedasticity)."
                    ),
                    "not_significant": (
                        "Homogeneity of variances is supported. "
                        "The samples have similar variances (homoscedasticity)."
                    ),
                },
                es={
                    "significant": (
                        "No se detecta homogeneidad de varianzas. "
                        "Las muestras tienen varianzas diferentes (heterocedasticidad)."
                    ),
                    "not_significant": (
                        "Se confirma homogeneidad de varianzas. "
                        "Las muestras tienen varianzas similares (homocedasticidad)."
                    ),
                },
                pt={
                    "significant": (
                        "Não há homogeneidade de variâncias detectada. "
                        "As amostras têm variâncias diferentes (heterocedasticidade)."
                    ),
                    "not_significant": (
                        "Há homogeneidade de variâncias. "
                        "As amostras têm variâncias similares (homocedasticidade)."
                    ),
                },
            ),
        }

    def get_schema(self) -> dict:
        """Schema for Levene's Test configuration."""
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

    def run(
        self,
        scores: dict[str, list[float]],  # {run_name: [fold_scores]}
        alpha: float = 0.05,
        **kwargs,
    ) -> StatisticalTestResult:
        import numpy as np
        from scipy.stats import levene

        if len(scores) < 2:
            raise ValueError("Levene's Test requires at least two sets of scores.")

        data = [np.array(scores[run_name]) for run_name in scores]
        statistic, p_value = levene(*data)

        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={},
        )
