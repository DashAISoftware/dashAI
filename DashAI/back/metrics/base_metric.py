"""Base Metric abstract class."""

from typing import Final


class BaseMetric:
    """Abstract class of all metrics.

    Attributes
    ----------
    HIGHER_IS_BETTER : bool
        Indicates the optimization direction for this metric.
        - True: Higher values are better (e.g., Accuracy, F1)
        - False: Lower values are better (e.g., MAE, RMSE, SMAPE)

        This attribute is used by hyperparameter optimizers to determine
        whether to maximize or minimize the metric during optimization.
    """

    TYPE: Final[str] = "Metric"

    # Default: metrics should minimize (most are error/loss metrics)
    # Subclasses should override this for metrics where higher is better
    HIGHER_IS_BETTER: bool = False
