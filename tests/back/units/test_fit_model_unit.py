"""Tests for FitModelUnit's validation, independent of an actual training run."""

import pytest
from kink import di

from DashAI.back.job.base_job import JobError
from DashAI.back.optimizers.optuna_optimizer import OptunaOptimizer
from DashAI.back.units.context import ExecutionContext, UnitContractError
from DashAI.back.units.fit_model_unit import FitModelUnit

# Two trials over one hyperparameter: the shape create_plots expects,
# small enough that only the filenames are under test here.
_TRIALS = [
    {"params": {"C": 0.1}, "value": 0.5},
    {"params": {"C": 1.0}, "value": 0.9},
]
_GOAL_METRIC = {"name": "Accuracy", "metadata": {"maximize": True}}


def _unit(
    optimizer_name="OptunaOptimizer",
    goal_metric="Accuracy",
    run_id=None,
    artifact_prefix=None,
):
    # run_id and artifact_prefix are read straight from the config, with no
    # default: omitting one is a KeyError rather than a silently disabled
    # runtime-state assertion or a plot filename nobody chose.
    return FitModelUnit(
        optimizer={"component": optimizer_name, "params": {}},
        goal_metric=goal_metric,
        run_id=run_id,
        artifact_prefix=artifact_prefix,
    )


def test_validate_raises_when_called_before_build_model_unit_has_run():
    """Regression: a missing key must not read as "nothing to optimize".

    ``optimizable_parameters`` is only absent from the context when
    ``BuildModelUnit`` hasn't run yet — a call-order mistake, not a model with
    no optimizable parameters (that case has the key present but empty).
    Before this fix, ``validate`` used ``ctx.get`` and treated both the same,
    silently skipping the optimizer/goal-metric checks it exists to run.
    """
    ctx = ExecutionContext()

    with pytest.raises(UnitContractError, match="'optimizable_parameters'"):
        _unit().validate(ctx)


def test_validate_is_a_noop_when_there_are_genuinely_no_optimizable_parameters():
    ctx = ExecutionContext()
    ctx.put("optimizable_parameters", [])

    # Should not raise, and should not need the optimizer/goal_metric to
    # resolve in the registry.
    unit = _unit(optimizer_name="DoesNotExist", goal_metric="DoesNotExist")
    unit.validate(ctx)

    assert unit._optimizer is None
    assert unit._goal_metric is None


def test_the_optimizer_is_kept_on_the_unit_not_in_the_shared_context():
    """Regression: the optimizer is this unit's own state, not an output.

    It used to be written to the context by ``validate`` and read back by
    ``execute``, using the shared context as a scratchpad between one unit's
    own two phases. Two FitModelUnits in one context would overwrite each
    other's optimizer, and the second would silently run the first one's.
    """

    class _Optimizer:
        def __init__(self, **params):
            pass

    registry = {
        "AnOptimizer": {"class": _Optimizer},
        "Accuracy": {"class": object, "metadata": {"maximize": True}},
    }
    di["component_registry"] = registry
    try:
        ctx = ExecutionContext()
        ctx.put("optimizable_parameters", ["lr"])

        unit = _unit(optimizer_name="AnOptimizer")
        unit.validate(ctx)

        assert isinstance(unit._optimizer, _Optimizer)
        assert not ctx.has("optimizer")
        assert not ctx.has("goal_metric")
    finally:
        del di["component_registry"]


def test_the_plot_filenames_come_from_the_artifact_prefix_when_there_is_one():
    """A caller that is not a run names the plots itself.

    Two pipeline executions have no run id to tell them apart, so without a
    prefix both would write ``history_objective_plot_None.pickle`` into the
    shared runs directory and the second would overwrite the first.
    """
    optimizer = OptunaOptimizer()

    filenames, _ = optimizer.create_plots(
        _TRIALS,
        None,
        n_params=1,
        goal_metric=_GOAL_METRIC,
        artifact_prefix="pipeline-3-fit",
    )

    assert filenames == [
        "history_objective_plot_pipeline-3-fit.pickle",
        "slice_plot_pipeline-3-fit.pickle",
    ]


def test_without_an_artifact_prefix_the_filenames_still_come_from_the_run_id():
    """The default has to leave a real run's filenames exactly as they were."""
    optimizer = OptunaOptimizer()

    named_by_default, _ = optimizer.create_plots(
        _TRIALS, 42, n_params=1, goal_metric=_GOAL_METRIC
    )
    named_explicitly, _ = optimizer.create_plots(
        _TRIALS, 42, n_params=1, goal_metric=_GOAL_METRIC, artifact_prefix=None
    )

    assert named_by_default == [
        "history_objective_plot_42.pickle",
        "slice_plot_42.pickle",
    ]
    assert named_explicitly == named_by_default


class _Detached:
    """What an optimizer must never return: a model with no data attached."""

    x_data = None
    run_id = None


class _Attached:
    """What ModelFactory produces: the splits hang off the instance."""

    x_data = {"train": "x"}
    run_id = None


def test_a_model_detached_from_its_data_is_refused_even_with_no_run():
    """The guard used to key on run_id, which made it a no-op for a pipeline.

    A pipeline always has run_id None, so returning early on that skipped the
    check for the one caller with no other signal: it would finish with an
    empty metrics artifact instead of an error. What both callers need is that
    the model still carries what scoring reads, so that is what is checked.
    """
    with pytest.raises(JobError, match="detached from its data"):
        FitModelUnit._assert_model_keeps_its_runtime_state(_Detached())


def test_a_model_that_kept_its_data_passes_without_a_run():
    FitModelUnit._assert_model_keeps_its_runtime_state(_Attached())
