from DashAI.back.core.utils import MultilingualString
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult


class ShapiroTest(BaseStatisticalTest):
    """Test for normality of a single set of scores."""

    DISPLAY_NAME: str = MultilingualString(
        en="Shapiro-Wilk Test",
        es="Prueba de Shapiro-Wilk",
        pt="Teste de Shapiro-Wilk",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Normality test that assesses whether the data comes from ",
            "a normal distribution.",
        ),
        es=(
            "Prueba de normalidad que evalúa si los datos provienen de ",
            "una distribución normal.",
        ),
        pt=(
            "Teste de normalidade que avalia se os dados vêm de uma",
            "distribuição normal.",
        ),
    )
    ICON: str = "ShowChart"
    COLOR: str = "#4CAF50"

    @classmethod
    def get_metadata(cls) -> dict:
        """Metadata for Shapiro-Wilk Test."""
        return {
            "icon": cls.ICON,
            "is_parametric": None,
            "is_posthoc": False,
            "min_runs": 1,
            "max_runs": None,
            "per_run": True,
            "supports_alternative": False,
            "supports_correction": False,
            "interpretation": MultilingualString(
                en={
                    "significant": (
                        "Data does not follow a normal distribution. "
                        "The assumption of normality is violated."
                    ),
                    "not_significant": (
                        "Data appears to follow a normal distribution. "
                        "The assumption of normality is satisfied."
                    ),
                },
                es={
                    "significant": (
                        "Los datos no siguen una distribución normal. "
                        "Se viola el supuesto de normalidad."
                    ),
                    "not_significant": (
                        "Los datos parecen seguir una distribución normal. "
                        "Se cumple el supuesto de normalidad."
                    ),
                },
                pt={
                    "significant": (
                        "Os dados não seguem uma distribuição normal. "
                        "A suposição de normalidade é violada."
                    ),
                    "not_significant": (
                        "Os dados parecem seguir uma distribuição normal. "
                        "A suposição de normalidade é satisfeita."
                    ),
                },
            ),
        }

    def get_schema(self) -> dict:
        """Schema for Shapiro-Wilk Test configuration."""
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
        from scipy.stats import shapiro

        if len(scores) != 1:
            raise ValueError("Shapiro-Wilk Test requires exactly one set of scores.")

        run_name = list(scores.keys())[0]
        data = np.array(scores[run_name])

        statistic, p_value = shapiro(data)
        significant = p_value < alpha

        return StatisticalTestResult(
            statistic=statistic,
            p_value=float(p_value),
            significant=significant,
            alpha=alpha,
            details={"run": run_name, "data": data.tolist()},
        )
