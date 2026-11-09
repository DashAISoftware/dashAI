"""The figures of the Forecasts view, drawn from a backtest's saved forecasts."""

from typing import Any, Dict, List, Optional, Union

from DashAI.back.core.artifacts import (
    ArtifactGroup,
    GroupedArtifacts,
    PlotlyArtifact,
)
from DashAI.back.core.utils import MultilingualString

ACTUAL_COLOR = "#42a5f5"
FORECAST_COLOR = "#ffa726"
FORECAST_RGB = "255, 167, 38"

LABELS = {
    "actual": MultilingualString(
        en="Actual", es="Real", pt="Real", de="Tatsächlich", zh="实际值"
    ),
    "forecast": MultilingualString(
        en="Forecast", es="Pronóstico", pt="Previsão", de="Prognose", zh="预测值"
    ),
    "forecasts": MultilingualString(
        en="Forecasts", es="Pronósticos", pt="Previsões", de="Prognosen", zh="预测"
    ),
    "interval": MultilingualString(
        en="{level}% interval",
        es="Intervalo del {level}%",
        pt="Intervalo de {level}%",
        de="{level}%-Intervall",
        zh="{level}% 区间",
    ),
    "validation": MultilingualString(
        en="Validation", es="Validación", pt="Validação", de="Validierung", zh="验证"
    ),
    "test": MultilingualString(
        en="Test", es="Prueba", pt="Teste", de="Test", zh="测试"
    ),
    "date": MultilingualString(en="Date", es="Fecha", pt="Data", de="Datum", zh="日期"),
    "value": MultilingualString(en="Value", es="Valor", pt="Valor", de="Wert", zh="值"),
}


def _origin_labels(origins: List[Dict[str, Any]], lang: str) -> List[str]:
    """Name each origin by its partition, numbered when the partition has several.

    Parameters
    ----------
    origins : list of dict
        The origins of the forecasts file, each with ``partition`` and
        ``index``.
    lang : str
        The language to name the partitions in.

    Returns
    -------
    list of str
        One label per origin, in the same order.
    """
    counts: Dict[str, int] = {}
    for origin in origins:
        counts[origin["partition"]] = counts.get(origin["partition"], 0) + 1
    labels = []
    for origin in origins:
        partition = origin["partition"]
        name = LABELS[partition].get(lang) if partition in LABELS else partition
        labels.append(
            f"{name} {origin['index'] + 1}" if counts[partition] > 1 else name
        )
    return labels


def _origin_figure(
    origin: Dict[str, Any], levels: List[int], title: str, lang: str
) -> PlotlyArtifact:
    """Draw one origin: its interval bands, what happened and the forecast.

    Parameters
    ----------
    origin : dict
        One origin of the forecasts file: ``dates``, ``actual``, ``forecast``
        and the ``lower`` and ``upper`` bounds by level.
    levels : list of int
        The interval levels the file carries.
    title : str
        The title of the figure.
    lang : str
        The language of the trace and axis names.

    Returns
    -------
    PlotlyArtifact
        The figure. A level whose bounds the origin lacks gets no band, and
        the widest band is drawn first so a narrower one shows over it.
    """
    import plotly.graph_objects as go

    figure = go.Figure()
    for position, level in enumerate(sorted(levels, reverse=True)):
        lower = origin.get("lower", {}).get(str(level))
        upper = origin.get("upper", {}).get(str(level))
        if not lower or not upper:
            continue
        name = LABELS["interval"].get(lang).format(level=level)
        figure.add_trace(
            go.Scatter(
                x=origin["dates"],
                y=upper,
                mode="lines",
                name=name,
                legendgroup=name,
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=origin["dates"],
                y=lower,
                mode="lines",
                name=name,
                legendgroup=name,
                line={"width": 0},
                fill="tonexty",
                fillcolor=f"rgba({FORECAST_RGB}, {0.15 + 0.1 * position:.2f})",
            )
        )
    figure.add_trace(
        go.Scatter(
            x=origin["dates"],
            y=origin["actual"],
            mode="lines+markers",
            name=LABELS["actual"].get(lang),
            line={"color": ACTUAL_COLOR},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=origin["dates"],
            y=origin["forecast"],
            mode="lines+markers",
            name=LABELS["forecast"].get(lang),
            line={"color": FORECAST_COLOR, "dash": "dash"},
        )
    )
    figure.update_layout(
        title=title,
        xaxis={"type": "date", "title": LABELS["date"].get(lang)},
        yaxis={"title": LABELS["value"].get(lang)},
        legend={"orientation": "h"},
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return PlotlyArtifact(payload=figure, title=title)


def forecasts_artifacts(
    forecasts: Dict[str, Any], accept_language: Optional[str] = None
) -> List[Union[PlotlyArtifact, GroupedArtifacts]]:
    """Build the Forecasts view of a run from its saved forecasts.

    Every model's own intervals arrive as the ``lower`` and ``upper`` bounds
    it gave at each step, so the same drawing serves all of them.

    Parameters
    ----------
    forecasts : dict
        The run's forecasts file: ``levels`` and ``origins``, each origin
        with its ``partition``, ``index``, ``dates``, ``actual``,
        ``forecast`` and the ``lower`` and ``upper`` bounds by level.
    accept_language : str, optional
        The request's ``Accept-Language`` header. Defaults to English.

    Returns
    -------
    list
        A single figure when the backtest had one origin, otherwise one
        selector holding a figure per origin. Empty without origins.
    """
    lang = (accept_language or "en").split(",")[0].split("-")[0].strip() or "en"
    origins = forecasts.get("origins") or []
    levels = [int(level) for level in forecasts.get("levels") or []]
    heading = LABELS["forecasts"].get(lang)
    labels = _origin_labels(origins, lang)
    figures = [
        _origin_figure(origin, levels, f"{heading} ({label})", lang)
        for origin, label in zip(origins, labels, strict=True)
    ]
    if len(figures) <= 1:
        return figures
    return [
        GroupedArtifacts(
            title=heading,
            groups=[
                ArtifactGroup(title=label, artifacts=[figure])
                for label, figure in zip(labels, figures, strict=True)
            ],
        )
    ]
