# normality_check.py
import numpy as np
from scipy.stats import shapiro


def check_normality(
    scores: dict[str, list[float]],
    alpha: float = 0.05,
) -> dict[str, dict]:
    """
    Returns per-run normality check results.
    {
        "RandomForest_1": {
            "statistic": 0.94,
            "p_value": 0.43,
            "is_normal": True
        },
        ...
    }
    """
    results = {}
    for run_name, fold_scores in scores.items():
        arr = np.array(fold_scores)
        statistic, p_value = shapiro(arr)
        results[run_name] = {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "is_normal": p_value >= alpha,
        }
    return results


def all_normal(normality_results: dict) -> bool:
    return all(r["is_normal"] for r in normality_results.values())
