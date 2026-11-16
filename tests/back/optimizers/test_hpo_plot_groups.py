"""HPO plots with one figure per option are a group of artifacts, not a dropdown."""

import json

from DashAI.back.core.artifacts import GroupedArtifacts, PlotlyArtifact
from DashAI.back.optimizers.optuna_optimizer import OptunaOptimizer
from tests.back.optimizers.test_categorical_search import (
    GOAL_METRIC,
    DummyModel,
    _plot_trials,
)

TRIALS = _plot_trials(
    [
        ({"max_depth": 3, "min_samples_split": 2}, 0.80),
        ({"max_depth": 6, "min_samples_split": 3}, 0.87),
        ({"max_depth": 9, "min_samples_split": 4}, 0.85),
    ]
)


def _optimizer(*names):
    model = DummyModel()
    optimizer = OptunaOptimizer(n_trials=3, sampler="RandomSampler", pruner=None)
    optimizer.parameters = [(model, name, (2, 10), "integer") for name in names]
    return optimizer


def _figure(artifact):
    return json.loads(artifact.payload)


def test_a_slice_over_several_parameters_is_a_group_per_parameter():
    plot = _optimizer("max_depth", "min_samples_split").slice_plot(TRIALS, GOAL_METRIC)

    assert isinstance(plot, GroupedArtifacts)
    assert [group.title for group in plot.groups] == ["max_depth", "min_samples_split"]
    for group in plot.groups:
        [artifact] = group.artifacts
        figure = _figure(artifact)
        assert "updatemenus" not in figure["layout"]
        assert len(figure["data"]) == 1
        assert figure["layout"]["xaxis"]["title"]["text"] == group.title
        assert figure["data"][0]["x"] == [
            trial["params"][group.title] for trial in TRIALS
        ]


def test_a_slice_over_one_parameter_is_a_single_figure():
    trials = _plot_trials([({"max_depth": 3}, 0.8), ({"max_depth": 6}, 0.9)])

    plot = _optimizer("max_depth").slice_plot(trials, GOAL_METRIC)

    assert isinstance(plot, PlotlyArtifact)
    assert "updatemenus" not in _figure(plot)["layout"]


def test_a_contour_is_a_group_per_pair_of_parameters():
    plot = _optimizer("max_depth", "min_samples_split").contour_plot(
        TRIALS, GOAL_METRIC
    )

    assert isinstance(plot, GroupedArtifacts)
    assert [group.title for group in plot.groups] == [
        "max_depth vs min_samples_split",
        "min_samples_split vs max_depth",
    ]
    for group in plot.groups:
        [artifact] = group.artifacts
        figure = _figure(artifact)
        param_x, param_y = group.title.split(" vs ")
        assert "updatemenus" not in figure["layout"]
        assert [trace["type"] for trace in figure["data"]] == ["contour", "scatter"]
        assert figure["layout"]["xaxis"]["title"]["text"] == param_x
        assert figure["layout"]["yaxis"]["title"]["text"] == param_y
