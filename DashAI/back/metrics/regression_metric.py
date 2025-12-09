from DashAI.back.metrics.base_metric import BaseMetric


class RegressionMetric(BaseMetric):
    """Class for metrics associated with regression models."""

    MAXIMIZE: bool = False
    COMPATIBLE_COMPONENTS = ["RegressionTask"]
