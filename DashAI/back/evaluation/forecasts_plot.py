"""The figures of the Forecasts view, drawn from a backtest's saved forecasts."""

from typing import Any, Dict, List, Union

from DashAI.back.core.artifacts import (
    ArtifactGroup,
    GroupedArtifacts,
    PlotlyArtifact,
)

ACTUAL_COLOR = "#42a5f5"
FORECAST_COLOR = "#ffa726"
FORECAST_RGB = "255, 167, 38"
PARTITIONS = {"validation": "Validation", "test": "Test"}


def _origin_labels(origins: List[Dict[str, Any]]) -> List[str]:
    """Name each origin by its partition, numbered when the partition has several.

    Parameters
    ----------
    origins : list of dict
        The origins of the forecasts file, each with ``partition`` and
        ``index``.

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
        name = PARTITIONS.get(partition, partition)
        labels.append(
            f"{name} {origin['index'] + 1}" if counts[partition] > 1 else name
        )
    return labels


def _origin_figure(
    origin: Dict[str, Any], levels: List[int], title: str
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
        name = f"{level}% interval"
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
            name="Actual",
            line={"color": ACTUAL_COLOR},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=origin["dates"],
            y=origin["forecast"],
            mode="lines+markers",
            name="Forecast",
            line={"color": FORECAST_COLOR, "dash": "dash"},
        )
    )
    figure.update_layout(
        title=title,
        xaxis={"type": "date", "title": "Date"},
        yaxis={"title": "Value"},
        legend={"orientation": "h"},
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return PlotlyArtifact(payload=figure, title=title)


def forecasts_artifacts(
    forecasts: Dict[str, Any],
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

    Returns
    -------
    list
        A single figure when the backtest had one origin, otherwise one
        selector holding a figure per origin. Empty without origins.
    """
    origins = forecasts.get("origins") or []
    levels = [int(level) for level in forecasts.get("levels") or []]
    labels = _origin_labels(origins)
    figures = [
        _origin_figure(origin, levels, f"Forecasts ({label})")
        for origin, label in zip(origins, labels, strict=True)
    ]
    if len(figures) <= 1:
        return figures
    return [
        GroupedArtifacts(
            title="Forecasts",
            groups=[
                ArtifactGroup(title=label, artifacts=[figure])
                for label, figure in zip(labels, figures, strict=True)
            ],
        )
    ]
