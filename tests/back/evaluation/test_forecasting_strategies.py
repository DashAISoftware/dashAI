"""Evaluation strategies that know what a forecast is.

What the ordinary strategies assume and a forecaster does not share is the
training partition being worth scoring. For a forecaster that means asking a
model about dates it was fitted on. That is a fit statistic, not a forecast,
and putting the two in one results table invites a comparison that means
nothing.

How a forecasting run fits its kept model is no longer these strategies' x/y
units' business: the backtest fits it on the whole series (RECONCILING_FORECASTING
§2.13). The tests that pinned the old final fit, which stopped at the end of
the training rows, went with it.
"""

import pandas as pd
import pytest

from DashAI.back.core.enums.metrics import SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.evaluation.cv import CrossValidationEvaluationStrategy
from DashAI.back.evaluation.forecasting_cv import (
    ForecastingCrossValidationEvaluationStrategy,
)
from DashAI.back.evaluation.forecasting_holdout import (
    ForecastingHoldoutEvaluationStrategy,
)
from DashAI.back.evaluation.holdout import HoldoutEvaluationStrategy
from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter

FORECASTING_STRATEGIES = [
    ForecastingHoldoutEvaluationStrategy,
    ForecastingCrossValidationEvaluationStrategy,
]


def _split(n=60):
    season = [10.0, 20.0, 30.0, 40.0, 35.0, 25.0, 15.0, 12.0, 18.0, 28.0, 38.0, 22.0]
    values = [v + i * 0.8 for i, v in enumerate(season * (n // 12))]
    dates = pd.date_range("2022-01-01", periods=n, freq="MS").strftime("%Y-%m-%d")
    dataset = transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame({"date": dates.tolist(), "v": values})),
        {
            "date": {"type": "Date", "dtype": "%Y-%m-%d"},
            "v": {"type": "Float", "dtype": "float64"},
        },
    )
    x, y = select_columns(dataset, ["date"], ["v"])
    return TemporalHoldoutSplitter(
        {"train": 0.6, "validation": 0.2, "test": 0.2}
    ).split(x, y)


# --- what each strategy declares ---------------------------------------------


@pytest.mark.parametrize("strategy", FORECASTING_STRATEGIES)
def test_forecasting_strategies_serve_forecasting(strategy):
    assert strategy.COMPATIBLE_COMPONENTS == ["SingleSeriesForecastingTask"]


def test_the_ordinary_strategies_no_longer_serve_forecasting():
    for strategy in (HoldoutEvaluationStrategy, CrossValidationEvaluationStrategy):
        assert "SingleSeriesForecastingTask" not in strategy.COMPATIBLE_COMPONENTS
        assert "RegressionTask" in strategy.COMPATIBLE_COMPONENTS


def test_each_strategy_declares_the_shape_of_its_splits():
    # The frontend renders holdout controls or fold controls from this rather
    # than from the strategy's class name, which it used to compare against.
    assert ForecastingHoldoutEvaluationStrategy.get_metadata()["kind"] == "holdout"
    assert HoldoutEvaluationStrategy.get_metadata()["kind"] == "holdout"
    assert ForecastingCrossValidationEvaluationStrategy.get_metadata()["kind"] == "cv"
    assert CrossValidationEvaluationStrategy.get_metadata()["kind"] == "cv"


# --- which partitions get scored ---------------------------------------------


def test_each_strategy_declares_which_partitions_it_scores():
    """The fold charts build one toggle per scored partition.

    Reading it from the strategy is what stops them from asking for the train
    fold metrics a forecasting run never wrote.
    """
    assert ForecastingCrossValidationEvaluationStrategy.get_metadata()[
        "scored_splits"
    ] == ["validation", "test"]
    assert ForecastingHoldoutEvaluationStrategy.get_metadata()["scored_splits"] == [
        "validation",
        "test",
    ]
    assert CrossValidationEvaluationStrategy.get_metadata()["scored_splits"] == [
        "train",
        "validation",
        "test",
    ]
    assert HoldoutEvaluationStrategy.get_metadata()["scored_splits"] == [
        "train",
        "validation",
        "test",
    ]


@pytest.mark.parametrize("strategy", FORECASTING_STRATEGIES)
def test_forecasting_strategies_do_not_score_the_training_partition(strategy):
    assert SplitEnum.TRAIN not in strategy.SCORED_SPLITS


def test_the_holdout_strategy_scores_validation_and_test():
    assert ForecastingHoldoutEvaluationStrategy.SCORED_SPLITS == (
        SplitEnum.VALIDATION,
        SplitEnum.TEST,
    )


def test_the_ordinary_holdout_strategy_still_scores_all_three():
    assert HoldoutEvaluationStrategy.SCORED_SPLITS == (
        SplitEnum.TRAIN,
        SplitEnum.VALIDATION,
        SplitEnum.TEST,
    )


def _fit_unit(**overrides):
    """A FitModelUnit configured for an ordinary run.

    The strategies declare how a run is evaluated; this unit is what carries it
    out. The tests below live next to the declarations because that is the pair
    that has to stay consistent -- a strategy that says it does not score the
    training partition, and a fit that then does not.
    """
    from DashAI.back.units.fit_model_unit import FitModelUnit

    config = {
        "optimizer": {"component": "", "params": {}},
        "goal_metric": "",
        "run_id": None,
        "artifact_prefix": None,
    }
    config.update(overrides)
    return FitModelUnit(**config)


# --- hyperparameter trials ---------------------------------------------------


class _RecordingModel:
    """Stands in for a model, noting which partitions it is asked to score."""

    def __init__(self):
        self.scored = []

    def train(self, *args, **kwargs):
        return self

    def predict(self, x):
        import numpy as np

        return np.zeros(len(x))

    def prepare_output(self, y, is_fit=False):
        return y

    def calculate_metrics(self, split, level=None, **kwargs):
        self.scored.append(split)


def _trial_of(strategy_class):
    """Run one trial configured the way this strategy's runs are configured.

    Which partitions a trial records is no longer the strategy's own code: the
    job reads SCORED_SPLITS off the class and hands it to the fitting unit,
    minus the test partition, which a trial may never score. This does the same
    thing so the declaration stays connected to what it produces.
    """
    from DashAI.back.metrics.regression.mae import MAE

    xs, ys, _ = _split()
    model = _RecordingModel()
    trial_splits = [
        split.name
        for split in strategy_class.SCORED_SPLITS
        if split is not SplitEnum.TEST
    ]

    _fit_unit(trial_splits=trial_splits)._score_one_trial(model, xs, ys, MAE)
    return model.scored


def test_a_forecasting_trial_never_scores_the_training_partition():
    scored = _trial_of(ForecastingHoldoutEvaluationStrategy)

    assert SplitEnum.TRAIN not in scored
    assert SplitEnum.VALIDATION in scored


def test_an_ordinary_trial_still_scores_both():
    scored = _trial_of(HoldoutEvaluationStrategy)

    assert SplitEnum.TRAIN in scored
    assert SplitEnum.VALIDATION in scored
