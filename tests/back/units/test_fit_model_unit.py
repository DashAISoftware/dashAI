"""Tests for FitModelUnit's validation, independent of an actual training run."""

import pytest
from kink import di

from DashAI.back.units.context import ExecutionContext, UnitContractError
from DashAI.back.units.fit_model_unit import FitModelUnit


def _unit(optimizer_name="OptunaOptimizer", goal_metric="Accuracy"):
    return FitModelUnit(
        optimizer={"component": optimizer_name, "params": {}},
        goal_metric=goal_metric,
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
