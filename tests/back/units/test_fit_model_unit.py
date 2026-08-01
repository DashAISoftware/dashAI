"""Tests for FitModelUnit's validation, independent of an actual training run."""

import pytest

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
    _unit(optimizer_name="DoesNotExist", goal_metric="DoesNotExist").validate(ctx)

    assert not ctx.has("optimizer")
    assert not ctx.has("goal_metric")
