"""Tests for the shared plotly helpers used by model artifacts."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeClassifier

from DashAI.back.models.model_artifact_context import ModelArtifactContext
from DashAI.back.models.model_artifact_plots import (
    plot_feature_importances,
    plot_sklearn_tree,
    plot_weight_heatmap,
)


@pytest.fixture
def context():
    return ModelArtifactContext(
        feature_names=["wide", "narrow", "mid"],
        class_names=["low", "high"],
    )


@pytest.fixture
def training_frame():
    rng = np.random.default_rng(0)
    x = pd.DataFrame(
        {
            "wide": rng.normal(0, 5, 60),
            "narrow": rng.normal(0, 0.01, 60),
            "mid": rng.normal(0, 1, 60),
        }
    )
    return x, (x["wide"] > 0).astype(int).to_numpy()


def _figure(artifact):
    assert artifact.type == "plotly"
    return json.loads(artifact.payload)


def test_plot_sklearn_tree_has_one_point_per_node(context, training_frame):
    x, y = training_frame
    tree = DecisionTreeClassifier(max_depth=2, random_state=0).fit(x, y)

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


def test_no_builder_calls_predict():
    """Model visualizations render parameters, never model behavior.

    A builder that swept a feature range and read ``predict`` would be a global
    explainer, so none of them may take an estimator at all.
    """
    import inspect

    from DashAI.back.models import model_artifact_plots

    public = [name for name in dir(model_artifact_plots) if name.startswith("plot_")]
    for name in public:
        parameters = inspect.signature(getattr(model_artifact_plots, name)).parameters
        assert "model" not in parameters, f"{name} takes a model"
