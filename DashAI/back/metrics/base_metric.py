"""Base Metric abstract class."""

from typing import Any, Dict, Final


def cannot_be_optimized(metric_name: str) -> str:
    """Why a search cannot be run for a metric that is not ``OPTIMIZABLE``.

    Said by the run API, which refuses such a goal metric, and by the job,
    which guards the runs that do not come through the API.
    """
    return (
        f"The optimization metric {metric_name} cannot be optimized: no "
        "direction makes it better, and searching for it would pick the "
        "parameters it rewards for the wrong reason (interval coverage rewards "
        "the widest intervals). Choose an error metric."
    )


class BaseMetric:
    """Abstract base class for all DashAI evaluation metrics.

    Every concrete metric must subclass ``BaseMetric`` (or one of its
    category subclasses) and implement a static ``score`` method. The concrete
    method signature depends on the evaluation family: supervised metrics use
    true outputs and predictions, while clustering metrics use feature data and
    discovered labels.

    Class attributes
    ----------------
    TYPE : str
        Always ``"Metric"``; used by the DashAI component registry.
    MAXIMIZE : bool
        ``True`` if higher values are better (e.g. accuracy, R²),
        ``False`` if lower values are better (e.g. MAE, RMSE).
    OPTIMIZABLE : bool
        ``False`` for a metric that no direction makes better, so a search
        cannot be run for it and no run is the best by it (interval coverage,
        good near its nominal level). ``True`` by default.
    metadata : dict
        Optional extra metadata surfaced to the frontend via
        :meth:`get_metadata`.
    """

    TYPE: Final[str] = "Metric"
    MAXIMIZE: Final[bool] = False
    OPTIMIZABLE: bool = True
    metadata: Dict[str, Any] = {}

    @classmethod
    def get_metadata(cls: "BaseMetric") -> Dict[str, Any]:
        """
        Get metadata values for the current metric.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata
        """
        meta: Dict[str, Any] = dict(getattr(cls, "metadata", {}) or {})
        meta["maximize"] = cls.MAXIMIZE
        meta["optimizable"] = cls.OPTIMIZABLE

        return meta
