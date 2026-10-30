"""What an evaluation strategy declares for the frontend to read.

The session wizard and the run screens used to decide on their own which
splitters pair with a strategy, which one to start on and which result views
a run has, from the strategy's ``kind`` or a splitter's name. The strategy
declares them instead, so a strategy the frontend has never seen still gets
its controls and its views.
"""

import pytest

from DashAI.back.evaluation.cv import CrossValidationEvaluationStrategy
from DashAI.back.evaluation.forecasting_cv import (
    ForecastingCrossValidationEvaluationStrategy,
)
from DashAI.back.evaluation.forecasting_holdout import (
    ForecastingHoldoutEvaluationStrategy,
)
from DashAI.back.evaluation.full_dataset import FullDatasetEvaluationStrategy
from DashAI.back.evaluation.holdout import HoldoutEvaluationStrategy
from DashAI.back.initial_components import get_initial_components

DECLARED = [
    (HoldoutEvaluationStrategy, "holdout", "HoldoutSplitter", []),
    (CrossValidationEvaluationStrategy, "folds", None, ["fold_metrics"]),
    (FullDatasetEvaluationStrategy, None, None, []),
    (
        ForecastingHoldoutEvaluationStrategy,
        "origins",
        "TemporalHoldoutSplitter",
        ["forecasts"],
    ),
    (
        ForecastingCrossValidationEvaluationStrategy,
        "origins",
        "RollingOriginSplitter",
        ["fold_metrics", "forecasts"],
    ),
]


@pytest.mark.parametrize(
    ("strategy", "partitioning", "default_splitter", "result_views"), DECLARED
)
def test_a_strategy_declares_its_splitters_and_its_result_views(
    strategy, partitioning, default_splitter, result_views
):
    metadata = strategy.get_metadata()

    assert metadata["splitter_partitioning"] == partitioning
    assert metadata["default_splitter"] == default_splitter
    assert metadata["result_views"] == result_views


@pytest.mark.parametrize(("strategy", "partitioning", "_default", "_views"), DECLARED)
def test_the_published_partitioning_is_the_one_the_session_api_checks(
    strategy, partitioning, _default, _views
):
    assert strategy.get_metadata()["splitter_partitioning"] == (
        strategy.SPLITTER_PARTITIONING
    )


@pytest.mark.parametrize(
    ("strategy", "partitioning", "default_splitter", "_views"),
    [row for row in DECLARED if row[2] is not None],
)
def test_a_default_splitter_carves_the_way_its_strategy_takes(
    strategy, partitioning, default_splitter, _views
):
    splitters = {
        component.__name__: component for component in get_initial_components()
    }

    offered = splitters[default_splitter]

    assert partitioning == offered.PARTITIONING


@pytest.mark.parametrize(
    ("strategy", "label"),
    [
        (HoldoutEvaluationStrategy, "Holdout"),
        (ForecastingHoldoutEvaluationStrategy, "Holdout"),
        (CrossValidationEvaluationStrategy, "Cross-Validation"),
        (ForecastingCrossValidationEvaluationStrategy, "Cross-Validation"),
    ],
)
def test_a_strategy_names_itself_for_the_wizard_toggle(strategy, label):
    # The wizard labelled the toggle by kind, from texts of its own.
    display_name = getattr(strategy, "DISPLAY_NAME", None)

    assert display_name is not None
    assert display_name.get("en") == label
