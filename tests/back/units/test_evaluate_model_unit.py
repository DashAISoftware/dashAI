"""Tests for EvaluateModelUnit's contract, independent of a real database."""

import pytest

from DashAI.back.units.context import ExecutionContext, UnitContractError
from DashAI.back.units.evaluate_model_unit import EvaluateModelUnit


def test_call_refuses_to_run_without_a_run_id():
    """Regression: a missing run_id must fail loudly, not silently no-op.

    The idempotency check filters an existing-metric query by ``run_id``; a
    silently-``None`` value would match no row regardless of what was already
    logged, and — if the model were also somehow detached from its run —
    ``BaseModel.calculate_metrics`` no-ops on a falsy ``run_id`` too. Before
    this fix ``run_id`` was read with ``ctx.get`` and absent from
    ``REQUIRES``, so the unit could "succeed" having written zero metrics
    instead of surfacing the missing wiring.
    """
    ctx = ExecutionContext()
    ctx.put("model", object())

    with pytest.raises(UnitContractError, match="'run_id'"):
        EvaluateModelUnit()(ctx)
