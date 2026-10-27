"""Residuals of the backtest's forecasts against time."""

from typing import Any, Dict, List

from DashAI.back.core.artifacts import Artifact, PlotlyArtifact
from DashAI.back.core.utils import MultilingualString
from DashAI.back.reports.base_report import ReportError
from DashAI.back.reports.forecasting.forecasting_report import (
    ForecastingReport,
    origin_label,
    residual_points,
)


class ResidualsOverTime(ForecastingReport):
    """Residual against date, one marker series per origin, with the zero line.

    The residual plot used by regression scatters residuals against the
    predicted value; forecasting plots them against time, because time is
    where the error pattern lives. Residuals that drift off zero mean the
    model is systematically behind or ahead of the series, and a repeating
    pattern means a missed seasonality.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Residuals Over Time",
        es="Residuos en el Tiempo",
        pt="Resíduos ao Longo do Tempo",
        de="Residuen über die Zeit",
        zh="残差随时间变化",
    )
    DESCRIPTION: str = MultilingualString(
        en="Residual of each backtest forecast against its date.",
        es="Residuo de cada pronóstico del backtest contra su fecha.",
        pt="Resíduo de cada previsão do backtest contra a sua data.",
        de="Residuum jeder Backtest-Prognose gegen ihr Datum.",
        zh="回测中每次预测的残差与其日期的对应关系。",
    )
    COLOR: str = "#EF5350"
    ICON: str = "Timeline"

    def __init__(self, **kwargs) -> None:
        """Initialise the report. It takes no parameters."""

    def compute_forecasts(self, forecasts: Dict[str, Any]) -> List[Artifact]:
        """Draw the zero line and each origin's residuals against the date.

        Raises
        ------
        ReportError
            If no forecast step has both an actual value and a forecast.
        """
        import plotly.graph_objects as go

        points = residual_points(forecasts)
        if not points:
            raise ReportError("No forecast step has a residual to draw.")

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=[points[0][0], points[-1][0]],
                y=[0, 0],
                mode="lines",
                name="Zero",
                line={"dash": "dash", "width": 1, "color": "#9e9e9e"},
                hoverinfo="skip",
            )
        )
        for origin in forecasts["origins"]:
            mine = [(date, value) for date, value, of in points if of is origin]
            if mine:
                figure.add_trace(
                    go.Scatter(
                        x=[date for date, _ in mine],
                        y=[value for _, value in mine],
                        mode="markers",
                        name=origin_label(origin),
                    )
                )
        figure.update_layout(
            title="Residuals over time",
            xaxis_title="Date",
            yaxis_title="Actual - forecast",
            margin={"l": 20, "r": 20, "t": 50, "b": 40},
        )
        return [PlotlyArtifact(payload=figure, title="Residuals over time")]
