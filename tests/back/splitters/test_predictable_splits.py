"""Which partitions of a run its saved model can actually be asked to predict.

For most tasks that is every partition the run has: a fitted classifier will
happily label the rows it was trained on. A forecaster has none to offer: its
run is a backtest whose cuts are steps, and its kept model is fitted on the
whole series and predicts by horizon.
"""

from DashAI.back.evaluation.forecasting_cv import (
    ForecastingCrossValidationEvaluationStrategy,
)
from DashAI.back.evaluation.forecasting_holdout import (
    ForecastingHoldoutEvaluationStrategy,
)
from DashAI.back.evaluation.holdout import HoldoutEvaluationStrategy
from DashAI.back.splitters.holdout import HoldoutSplitter
from DashAI.back.splitters.rolling_origin import RollingOriginSplitter
from DashAI.back.splitters.splits_payload import predictable_splits
from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter
from DashAI.back.tasks.single_series_forecasting_task import (
    SingleSeriesForecastingTask,
)
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask

BACKTEST_RUN = {
    "horizon": 2,
    "validation_origins": [6],
    "test_origin": 8,
    "n_steps": 10,
}

SHUFFLED_RUN = {
    "train_indexes": [0, 1, 2, 3, 4, 5],
    "val_indexes": [6, 7],
    "test_indexes": [8, 9],
}


def registry_for(splitter, task, strategy):
    """Build the smallest mapping the resolver needs."""
    return {
        splitter.__name__: {"class": splitter},
        task.__name__: {"class": task},
        strategy.__name__: {"class": strategy},
    }


def test_a_backtest_run_offers_no_partition_to_predict():
    # A forecasting run stores its cuts in steps, not partitions of rows: its
    # model is fitted on the whole series and predicts by horizon. Nothing of
    # the run is offered as rows to predict.
    for splitter, strategy in (
        (TemporalHoldoutSplitter, ForecastingHoldoutEvaluationStrategy),
        (RollingOriginSplitter, ForecastingCrossValidationEvaluationStrategy),
    ):
        registry = registry_for(splitter, SingleSeriesForecastingTask, strategy)

        assert (
            predictable_splits(
                {"splitter_name": splitter.__name__},
                BACKTEST_RUN,
                registry,
                task_name="SingleSeriesForecastingTask",
                evaluation_strategy=strategy.__name__,
            )
            == []
        )


def test_an_ordinary_task_keeps_every_partition_and_the_whole_dataset():
    registry = registry_for(
        HoldoutSplitter,
        TabularClassificationTask,
        HoldoutEvaluationStrategy,
    )

    assert predictable_splits(
        {"splitter_name": "HoldoutSplitter"},
        SHUFFLED_RUN,
        registry,
        task_name="TabularClassificationTask",
        evaluation_strategy="HoldoutEvaluationStrategy",
    ) == [
        {"name": "train", "rows": 6},
        {"name": "test", "rows": 2},
        {"name": "val", "rows": 2},
        {"name": "all", "rows": 10},
    ]


def test_an_unregistered_task_is_treated_as_an_ordinary_one():
    registry = {"HoldoutSplitter": {"class": HoldoutSplitter}}

    assert predictable_splits(
        {"splitter_name": "HoldoutSplitter"},
        SHUFFLED_RUN,
        registry,
        task_name="APluginTask",
        evaluation_strategy="APluginStrategy",
    ) == [
        {"name": "train", "rows": 6},
        {"name": "test", "rows": 2},
        {"name": "val", "rows": 2},
        {"name": "all", "rows": 10},
    ]
