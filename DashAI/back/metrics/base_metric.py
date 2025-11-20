"""Base Metric abstract class."""

from typing import Any, Dict, Final


class BaseMetric:
    """Abstract class of all metrics."""

    TYPE: Final[str] = "Metric"
    MAXIMIZE: Final[bool] = False
    metadata: Dict[str, Any] = {}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get metadata values for the current metric.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata
        """
        meta: Dict[str, Any] = dict(getattr(cls, "metadata", {}) or {})
        meta["maximize"] = cls.MAXIMIZE

        return meta
