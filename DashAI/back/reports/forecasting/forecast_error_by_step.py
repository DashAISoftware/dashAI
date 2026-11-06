"""Forecast error by step of the horizon."""

from typing import Any, Dict, List

from DashAI.back.core.artifacts import Artifact, PlotlyArtifact
from DashAI.back.core.utils import MultilingualString
from DashAI.back.reports.base_report import ReportError
from DashAI.back.reports.forecasting.forecasting_report import ForecastingReport


class ForecastErrorByStep(ForecastingReport):
    """Mean absolute error at each step of the horizon, validation and test.

    One number per run hides how the error grows with distance: a model can
    be good one step out and useless six steps out. Each bar is the mean
    absolute error of the forecasts made that many steps past their origin,
    over the validation origins, beside the test's error at the same step. A
    staircase that climbs steeply says to forecast less far, or to choose a
    model that holds up over the horizon the run needs.
    """

    DISPLAY_NAME: str = MultilingualString(
        en="Error by Horizon Step",
        es="Error por Paso del Horizonte",
        pt="Erro por Passo do Horizonte",
        de="Fehler nach Horizontschritt",
        zh="按预测步长的误差",
    )
    DESCRIPTION: str = MultilingualString(
        en="Mean absolute error at each step past the origin, validation and test.",
        es="Error absoluto medio en cada paso tras el origen, validación y test.",
        pt="Erro absoluto médio em cada passo após a origem, validação e teste.",
        de="Mittlerer absoluter Fehler je Schritt nach dem Ursprung.",
        zh="起点之后每一步的平均绝对误差，验证与测试。",
    )
    COLOR: str = "#AB47BC"
    ICON: str = "BarChart"

    def __init__(self, **kwargs) -> None:
        """Initialise the report. It takes no parameters."""

    def compute_forecasts(self, forecasts: Dict[str, Any]) -> List[Artifact]:
        """Draw the mean absolute error per step, one bar series per partition.

        Raises
        ------
        ReportError
            If no forecast step has both an actual value and a forecast.
        """
        import numpy as np
        import plotly.graph_objects as go

        horizon = int(forecasts["horizon"])
        steps = list(range(1, horizon + 1))
        figure = go.Figure()
        drawn = False
        for partition, name in (("validation", "Validation"), ("test", "Test")):
            errors: Dict[int, List[float]] = {step: [] for step in steps}
            for origin in forecasts["origins"]:
                if origin["partition"] != partition:
                    continue
                pairs = zip(origin["actual"], origin["forecast"], strict=True)
                for step, (actual, forecast) in enumerate(pairs, start=1):
                    if actual is not None and forecast is not None:
                        errors[step].append(abs(actual - forecast))
            means = [
                float(np.mean(errors[step])) if errors[step] else None for step in steps
            ]
            if any(value is not None for value in means):
                drawn = True
                figure.add_trace(go.Bar(x=steps, y=means, name=name))

        if not drawn:
            raise ReportError("No forecast step has an error to draw.")

        figure.update_layout(
            title="Error by horizon step",
            xaxis_title="Steps past the origin",
            yaxis_title="Mean absolute error",
            barmode="group",
            margin={"l": 20, "r": 20, "t": 50, "b": 40},
        )
        return [PlotlyArtifact(payload=figure, title="Error by horizon step")]
