"""End-to-end proof that a trial actually gets pruned.

The unit tests cover each piece: the reporter reports, the hook fires only for
epoch+validation, `TrialPruned` is raised. This one wires the real parts
together and checks the outcome Optuna records, which is what the feature is
for — a pruner that never prunes passes every unit test in the file next door.

Real, not stubbed: `OptunaOptimizer.optimize`, `BaseModel.calculate_metrics`
(where the hook lives), `_report_epoch`, and Optuna's own MedianPruner and
trial bookkeeping.

Stubbed: `_save_metrics` (persistence needs a database and is not what this
proves) and the training itself, which is replaced by a loop that improves by a
fixed amount per epoch. The loop calls `calculate_metrics` exactly as the five
models that train in epochs do — same split, same level, same log_index.
"""

import optuna
import pytest

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.models.base_model import BaseModel
from DashAI.back.optimizers.optuna_optimizer import OptunaOptimizer

EPOCHS = 12


class Score:
    """Metric class. Named because results are keyed by `metric.__name__`."""

    @staticmethod
    def score(y_true, y_pred):
        return y_pred


class SteppedModel(BaseModel):
    """A model whose quality is decided by `rate` and revealed epoch by epoch.

    Trials with a low rate look bad early, which is precisely the situation a
    pruner exists to cut short.
    """

    def __init__(self):
        self.run_id = 1
        self.rate = 1.0
        self.value = 0.0
        self.epochs_run = 0
        for split in SplitEnum:
            setattr(self, f"{split.value}_metrics", [Score])
        # The optimizer also asks for trial-level metrics without passing data,
        # so `calculate_metrics` falls back to what the model holds.
        self.x_data = {split.value: [0] for split in SplitEnum}
        self.y_data = {split.value: [0] for split in SplitEnum}

    def save(self, filename): ...

    def load(self, filename): ...

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        self.value = 0.0
        for epoch in range(EPOCHS):
            self.value += self.rate
            self.epochs_run += 1
            # Same call the real epoch loops make.
            self.calculate_metrics(
                split=SplitEnum.VALIDATION,
                level=LevelEnum.EPOCH,
                x_data=[0],
                y_data=[0],
                log_index=epoch + 1,
            )

    def predict(self, x_data):
        return self.value

    def prepare_output(self, y_data, is_fit=False):
        return y_data

    def _save_metrics(self, split, level, results, log_index=None):
        """Persistence is out of scope; the database is not what this proves."""


@pytest.fixture
def dataset():
    return {"train": [0], "validation": [0]}


def _run(pruner, n_trials=10):
    model = SteppedModel()
    optimizer = OptunaOptimizer(
        n_trials=n_trials, sampler="RandomSampler", pruner=pruner
    )
    optimizer.optimize(
        model,
        dataset := {"train": [0], "validation": [0]},
        dataset,
        [(model, "rate", (0.01, 10.0), "number")],
        {"class": Score, "metadata": {"maximize": True}},
        "TabularClassificationTask",
    )
    return optimizer, model


def _states(optimizer):
    return [t.state for t in optimizer.study.trials]


def test_a_bad_trial_is_actually_pruned():
    """The outcome that matters: Optuna records trials as PRUNED."""
    optimizer, _ = _run("MedianPruner")

    pruned = [s for s in _states(optimizer) if s is optuna.trial.TrialState.PRUNED]

    assert pruned, (
        "no trial was pruned. The pruner is inert: either the epoch metrics never "
        "reach the trial, or TrialPruned is being swallowed before Optuna sees it."
    )


def test_pruning_stops_training_early():
    """A pruned trial must cost fewer epochs than a completed one.

    Pruning that reports the right verdict but keeps training saves nothing,
    which is the whole point of early stopping.
    """
    _, with_pruning = _run("MedianPruner")
    _, without = _run("NopPruner")

    assert with_pruning.epochs_run < without.epochs_run, (
        f"pruning ran {with_pruning.epochs_run} epochs and no-pruning ran "
        f"{without.epochs_run}: the trials were cut short on paper only"
    )


def test_disabled_pruning_completes_every_trial():
    """The control. With pruning off nothing may be cut, or the test above proves nothing."""
    optimizer, model = _run("NopPruner")

    states = _states(optimizer)
    assert all(s is optuna.trial.TrialState.COMPLETE for s in states)
    assert model.epochs_run == EPOCHS * (len(states) + 1)  # +1: the final refit
