"""Plotly builders shared by the model artifact mixins.

Every builder renders parameters a fitted estimator already holds, never the
result of calling ``predict``. Probing a model's behavior over a feature range
belongs to a global explainer, and comparing predictions against the truth
belongs to a metric, so neither has a builder here.

Every builder returns a :class:`DashAI.back.core.artifacts.PlotlyArtifact`, the
same artifact type explainers already produce, so the frontend renders these
with its existing viewer and gets plot editing, fullscreen and PNG/SVG download
for free.

Plotly is used throughout rather than matplotlib: matplotlib reaches the
environment only as a transitive dependency of ``shap`` and is not declared in
``pyproject.toml``, so importing it here would rest on an undeclared package.
"""

from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from DashAI.back.core.artifacts import PlotlyArtifact

if TYPE_CHECKING:
    import numpy as np


def _tree_node_positions(tree: Any) -> Tuple[List[float], List[float]]:
    """Lay a scikit-learn tree out on a plane.

    Leaves are placed left to right in the order an in-order walk reaches them
    and every internal node sits at the midpoint of its two children, which
    keeps parents centred above their subtrees. Depth drives the vertical
    position so the root sits at the top.

    Parameters
    ----------
    tree : sklearn.tree._tree.Tree
        The ``tree_`` attribute of a fitted estimator.

    Returns
    -------
    Tuple[List[float], List[float]]
        The x and y coordinate of every node, indexed by node id.
    """
    x_positions = [0.0] * tree.node_count
    y_positions = [0.0] * tree.node_count
    next_leaf_slot = 0

    def place(node: int, depth: int) -> float:
        nonlocal next_leaf_slot
        y_positions[node] = -float(depth)
        left, right = tree.children_left[node], tree.children_right[node]
        if left == -1:
            x_positions[node] = float(next_leaf_slot)
            next_leaf_slot += 1
        else:
            left_x = place(left, depth + 1)
            right_x = place(right, depth + 1)
            x_positions[node] = (left_x + right_x) / 2
        return x_positions[node]

    place(0, 0)
    return x_positions, y_positions


def _tree_node_label(
    tree: Any,
    node: int,
    feature_names: List[str],
    class_names: Optional[List[str]],
) -> str:
    """Describe one tree node for its hover tooltip.

    Parameters
    ----------
    tree : sklearn.tree._tree.Tree
        The ``tree_`` attribute of a fitted estimator.
    node : int
        Id of the node to describe.
    feature_names : List[str]
        Names of the features the tree was fitted on.
    class_names : Optional[List[str]]
        Class labels in encoded order, or None for a regression tree.

    Returns
    -------
    str
        An HTML fragment with the split rule, impurity, sample count and either
        the class distribution or the predicted value.
    """
    lines = []
    if tree.children_left[node] != -1:
        feature_index = tree.feature[node]
        name = (
            feature_names[feature_index]
            if feature_index < len(feature_names)
            else f"feature {feature_index}"
        )
        lines.append(f"{name} <= {tree.threshold[node]:.3f}")
    else:
        lines.append("leaf")

    lines.append(f"impurity: {tree.impurity[node]:.3f}")
    lines.append(f"samples: {int(tree.n_node_samples[node])}")

    values = tree.value[node][0]
    if class_names is not None:
        counts = ", ".join(
            f"{class_names[i] if i < len(class_names) else i}: {value:.3g}"
            for i, value in enumerate(values)
        )
        lines.append(counts)
    else:
        lines.append(f"value: {values[0]:.4g}")
    return "<br>".join(lines)


def plot_sklearn_tree(
    tree: Any,
    feature_names: List[str],
    class_names: Optional[List[str]] = None,
    title: Optional[str] = None,
) -> PlotlyArtifact:
    """Draw a fitted scikit-learn tree as an interactive node link diagram.

    Parameters
    ----------
    tree : sklearn.tree._tree.Tree
        The ``tree_`` attribute of a fitted estimator, not the estimator.
    feature_names : List[str]
        Names of the features the tree was fitted on.
    class_names : Optional[List[str]]
        Class labels in encoded order, or None for a regression tree.
    title : Optional[str]
        Title shown above the figure.

    Returns
    -------
    PlotlyArtifact
        A figure whose last trace holds one point per tree node.
    """
    import plotly.graph_objects as go

    x_positions, y_positions = _tree_node_positions(tree)

    edge_x: List[Optional[float]] = []
    edge_y: List[Optional[float]] = []
    for node in range(tree.node_count):
        for child in (tree.children_left[node], tree.children_right[node]):
            if child == -1:
                continue
            edge_x.extend([x_positions[node], x_positions[child], None])
            edge_y.extend([y_positions[node], y_positions[child], None])

    is_leaf = [tree.children_left[node] == -1 for node in range(tree.node_count)]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"width": 1, "color": "#9e9e9e"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=x_positions,
            y=y_positions,
            mode="markers",
            marker={
                "size": 12,
                "color": ["#66bb6a" if leaf else "#42a5f5" for leaf in is_leaf],
                "line": {"width": 1, "color": "#37474f"},
            },
            text=[
                _tree_node_label(tree, node, feature_names, class_names)
                for node in range(tree.node_count)
            ],
            hoverinfo="text",
            showlegend=False,
        )
    )
    figure.update_layout(
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return PlotlyArtifact(payload=figure, title=title)


def plot_feature_importances(
    feature_names: List[str],
    importances: "np.ndarray",
    title: Optional[str] = None,
) -> PlotlyArtifact:
    """Draw feature importances as a horizontal bar chart.

    Bars are emitted in ascending order so that plotly, which draws the first
    category at the bottom, renders the largest importance at the top.

    Parameters
    ----------
    feature_names : List[str]
        Names of the features, aligned with ``importances``.
    importances : np.ndarray
        Importance score per feature.
    title : Optional[str]
        Title shown above the figure.

    Returns
    -------
    PlotlyArtifact
        A horizontal bar figure.
    """
    import numpy as np
    import plotly.graph_objects as go

    values = np.asarray(importances, dtype=float)
    order = np.argsort(values)
    figure = go.Figure(
        go.Bar(
            x=values[order].tolist(),
            y=[str(feature_names[i]) for i in order],
            orientation="h",
            marker={"color": "#42a5f5"},
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Importance",
        margin={"l": 20, "r": 20, "t": 50, "b": 40},
    )
    return PlotlyArtifact(payload=figure, title=title)


def plot_weight_heatmap(
    matrix: "np.ndarray",
    title: Optional[str] = None,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    row_labels: Optional[List[str]] = None,
) -> PlotlyArtifact:
    """Draw a weight matrix as a diverging heatmap centred on zero.

    Parameters
    ----------
    matrix : np.ndarray
        Two dimensional array of weights.
    title : Optional[str]
        Title shown above the figure.
    x_title : Optional[str]
        Label of the horizontal axis.
    y_title : Optional[str]
        Label of the vertical axis.
    row_labels : Optional[List[str]]
        Tick labels for the rows, typically the input feature names.

    Returns
    -------
    PlotlyArtifact
        A heatmap figure.
    """
    import numpy as np
    import plotly.graph_objects as go

    values = np.asarray(matrix, dtype=float)
    heatmap = go.Heatmap(z=values.tolist(), colorscale="RdBu", zmid=0)
    if row_labels is not None and len(row_labels) == values.shape[0]:
        heatmap.y = [str(label) for label in row_labels]

    figure = go.Figure(heatmap)
    figure.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        margin={"l": 20, "r": 20, "t": 50, "b": 40},
    )
    return PlotlyArtifact(payload=figure, title=title)
