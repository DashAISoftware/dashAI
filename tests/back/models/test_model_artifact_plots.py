"""Tests for the shared plotly helpers used by model artifacts."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier

from DashAI.back.models.model_artifact_context import ModelArtifactContext
from DashAI.back.models.model_artifact_plots import (
    plot_decision_surface,
    plot_feature_importances,
    plot_regression_curve,
    plot_sklearn_tree,
    plot_weight_heatmap,
    select_two_features,
)


@pytest.fixture
def context():
    rng = np.random.default_rng(0)
    x = pd.DataFrame(
        {
            "wide": rng.normal(0, 5, 60),
            "narrow": rng.normal(0, 0.01, 60),
            "mid": rng.normal(0, 1, 60),
        }
    )
    y = (x["wide"] > 0).astype(int).to_numpy()
    return ModelArtifactContext(
        x_train=x,
        y_train=y,
        feature_names=list(x.columns),
        class_names=["low", "high"],
    )


def _figure(artifact):
    assert artifact.type == "plotly"
    return json.loads(artifact.payload)


def test_plot_sklearn_tree_has_one_point_per_node(context):
    tree = DecisionTreeClassifier(max_depth=2, random_state=0).fit(
        context.x_train, context.y_train
    )
    figure = _figure(
        plot_sklearn_tree(tree.tree_, context.feature_names, context.class_names, "T")
    )
    node_trace = figure["data"][-1]
    assert len(node_trace["x"]) == tree.tree_.node_count
    assert figure["layout"]["title"]["text"] == "T"


def test_plot_feature_importances_sorts_descending():
    figure = _figure(plot_feature_importances(["a", "b", "c"], [0.1, 0.7, 0.2], "I"))
    assert list(figure["data"][0]["y"]) == ["a", "c", "b"]


def test_plot_weight_heatmap_carries_the_matrix():
    figure = _figure(
        plot_weight_heatmap(np.array([[1.0, 2.0], [3.0, 4.0]]), "W", "x", "y")
    )
    assert figure["data"][0]["type"] == "heatmap"
    assert [list(row) for row in figure["data"][0]["z"]] == [[1.0, 2.0], [3.0, 4.0]]


def test_select_two_features_picks_the_highest_variance_pair(context):
    assert select_two_features(context) == (0, 2)


def test_plot_decision_surface_contours_and_scatters(context):
    model = KNeighborsClassifier(n_neighbors=3).fit(context.x_train, context.y_train)
    figure = _figure(plot_decision_surface(model, context, "S"))
    types = {trace["type"] for trace in figure["data"]}
    assert "contour" in types
    assert "scatter" in types
    assert figure["layout"]["xaxis"]["title"]["text"] == "wide"


def test_plot_regression_curve_has_a_line_and_the_training_points(context):
    reg_context = ModelArtifactContext(
        x_train=context.x_train,
        y_train=context.y_train.astype(float),
        feature_names=context.feature_names,
        class_names=None,
    )
    model = KNeighborsRegressor(n_neighbors=3).fit(
        reg_context.x_train, reg_context.y_train
    )
    figure = _figure(plot_regression_curve(model, reg_context, "R"))
    modes = [trace.get("mode") for trace in figure["data"]]
    assert "markers" in modes
    assert "lines" in modes
    # The swept axis is the widest spread feature, not merely the second one
    # returned by select_two_features.
    assert figure["layout"]["xaxis"]["title"]["text"] == "wide"
