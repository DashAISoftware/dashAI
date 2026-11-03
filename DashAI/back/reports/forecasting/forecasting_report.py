"""The base of the reports that draw a backtest's saved forecasts."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from DashAI.back.core.artifacts import Artifact
from DashAI.back.reports.base_report import BaseReport, ReportError


class ForecastingReport(BaseReport):
    """A report of a forecasting run, drawn from the forecasts it saved.

    A forecasting run keeps the forecasts of every origin of its backtest
    (``GET /run/{id}/forecasts``): dates, what actually happened, the forecast
    and its bounds. Its reports read that, never the model: the kept model was
    fitted on the whole series, so asking it about any of those dates would
    report a fit, not the forecasts its metrics measured (D6). ``ReportJob``
    hands them to ``compute_forecasts``.

    Not a ``Base*`` class: the registry finds a report's type by the one
    ancestor named ``Base*`` with a ``TYPE``.
    """

    COMPATIBLE_COMPONENTS = ["SingleSeriesForecastingTask"]

    def compute(
        self,
        y_true,
        y_pred,
        class_names: Optional[List[str]] = None,
    ) -> List[Artifact]:
        """A forecasting report has no rows to draw: see ``compute_forecasts``.

        Raises
        ------
        ReportError
            Always.
        """
        raise ReportError(
            f"{type(self).__name__} draws the forecasts a backtest saved, not "
            "the predictions of a partition."
        )

    @abstractmethod
    def compute_forecasts(self, forecasts: Dict[str, Any]) -> List[Artifact]:
        """Build the artifacts from a run's saved forecasts.

        Parameters
        ----------
        forecasts : dict
            The run's forecasts file: ``freq``, ``horizon``, ``levels`` and
            ``origins``, each origin with its ``partition``, ``index``,
            ``dates``, ``actual``, ``forecast`` and the ``lower`` and
            ``upper`` bounds by level.

        Returns
        -------
        List[Artifact]
            The artifacts to render, in display order.
        """


def origin_label(origin: Dict[str, Any]) -> str:
    """What a plot calls an origin: its partition and, for validation, its index."""
    if origin["partition"] == "test":
        return "Test"
    return f"Validation {origin['index'] + 1}"


def residual_points(
    forecasts: Dict[str, Any],
) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Every forecast step with a residual, in date order.

    Returns
    -------
    list of (date, residual, origin)
        The residual is actual minus forecast. A step whose actual or forecast
        is missing (not a finite number when saved) has none and is left out.
    """
    points = [
        (date, actual - forecast, origin)
        for origin in forecasts["origins"]
        for date, actual, forecast in zip(
            origin["dates"], origin["actual"], origin["forecast"], strict=True
        )
        if actual is not None and forecast is not None
    ]
    return sorted(points, key=lambda point: point[0])
