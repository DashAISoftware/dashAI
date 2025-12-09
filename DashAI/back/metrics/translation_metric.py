from DashAI.back.metrics.base_metric import BaseMetric


class TranslationMetric(BaseMetric):
    """Class for metrics associated to translation models."""

    COMPATIBLE_COMPONENTS = ["TranslationTask"]
