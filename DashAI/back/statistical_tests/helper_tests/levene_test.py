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
            "posthoc": False,
            "min_runs": 2,
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
        )
