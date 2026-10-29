"""Each origin's forecast against what actually happened, over time."""

from typing import Any, Dict, List

from DashAI.back.core.artifacts import Artifact, PlotlyArtifact
from DashAI.back.core.utils import MultilingualString
from DashAI.back.reports.forecasting.forecasting_report import (
    ForecastingReport,
    origin_label,
)

#: The interval a plot shades around a forecast, when the model gave one.
BAND_LEVEL = "95"


class ForecastVsActual(ForecastingReport):
    """The actual series and every origin's forecast, against the dates.

    An error scalar says how far off the forecasts are on average; this says
    *where*. A forecast that tracks well early in its window and drifts later
    shows an error that compounds over the horizon, a line that runs parallel
    but offset shows a level bias, and an actual value outside the shaded 95%
    interval shows a model more confident than it had reason to be.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Forecast vs Actual",
        es="Pronóstico vs Real",
        pt="Previsão vs Real",
        de="Prognose gegen Tatsächlich",
        zh="预测值与实际值",
    )
    DESCRIPTION: str = MultilingualString(
        en="Each backtest forecast and its interval against the actual series.",
        es="Cada pronóstico del backtest y su intervalo contra la serie real.",
        pt="Cada previsão do backtest e o seu intervalo contra a série real.",
        de="Jede Backtest-Prognose mit Intervall gegen die tatsächliche Reihe.",
        zh="回测中每次预测及其区间与实际序列的对比。",
    )
    COLOR: str = "#42A5F5"
    ICON: str = "ShowChart"

    def __init__(self, **kwargs) -> None:
        """Initialise the report. It takes no parameters."""

    def compute_forecasts(self, forecasts: Dict[str, Any]) -> List[Artifact]:
        """Draw the actual series, then each origin's forecast and band.

        Returns
        -------
        List[Artifact]
            One figure: the actual values over every forecast date, and per
            origin its forecast with its 95% interval shaded when it has one.
        """
        import plotly.graph_objects as go

        actual = sorted(
            {
                date: value
                for origin in forecasts["origins"]
                for date, value in zip(origin["dates"], origin["actual"], strict=True)
            }.items()
        )
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=[date for date, _ in actual],
                y=[value for _, value in actual],
                mode="lines+markers",
                name="Actual",
                line={"width": 2, "color": "#42a5f5"},
            )
        )
        for origin in forecasts["origins"]:
            label = origin_label(origin)
            lower = origin.get("lower", {}).get(BAND_LEVEL)
            upper = origin.get("upper", {}).get(BAND_LEVEL)
            if lower and upper:
                figure.add_trace(
                    go.Scatter(
                        x=origin["dates"] + origin["dates"][::-1],
                        y=upper + lower[::-1],
                        fill="toself",
                        fillcolor="rgba(255, 167, 38, 0.15)",
                        line={"width": 0},
                        hoverinfo="skip",
                        name=f"{label}: {BAND_LEVEL}% interval",
                        showlegend=False,
                    )
                )
            figure.add_trace(
                go.Scatter(
                    x=origin["dates"],
                    y=origin["forecast"],
                    mode="lines",
                    name=f"{label}: forecast",
                    line={"width": 2, "color": "#ffa726", "dash": "dash"},
                )
            )
        figure.update_layout(
            title="Forecast vs actual",
            xaxis_title="Date",
            yaxis_title="Value",
            margin={"l": 20, "r": 20, "t": 50, "b": 40},
        )
        return [PlotlyArtifact(payload=figure, title="Forecast vs actual")]
